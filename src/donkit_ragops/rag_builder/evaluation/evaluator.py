"""Batch RAG evaluation engine.

Reads evaluation datasets (CSV/JSON), queries RAG service,
computes retrieval metrics, optionally calls external evaluation service
for generation metrics, and saves results.
"""

from __future__ import annotations

import ast
import asyncio
import csv
import io
import json
import time
from pathlib import Path
from typing import Any

import httpx
from loguru import logger

from donkit_ragops.rag_builder.evaluation.metrics import DocumentNormalizer, RAGMetrics

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def extract_answer_and_sources(answer_json: dict) -> tuple[str, list[str], list[str]]:
    """Extract answer, context IDs, and chunks from a RAG response.

    Args:
        answer_json: RAG service JSON response.

    Returns:
        Tuple of (answer_text, context_ids, chunks).
    """
    answer_text = answer_json.get("answer", "")

    context_raw = answer_json.get("context", "")
    if isinstance(context_raw, str):
        context_ids = [c.strip() for c in context_raw.split(",") if c.strip()]
    elif isinstance(context_raw, list):
        context_ids = context_raw
    else:
        context_ids = []

    chunks = answer_json.get("chunks", [])
    if not isinstance(chunks, list):
        chunks = [chunks] if chunks else []

    return answer_text, context_ids, chunks


def _has_real_value(value: Any) -> bool:
    """Check whether a value is a real (non-placeholder) value."""
    if value is None:
        return False
    if isinstance(value, list):
        return any(_has_real_value(v) for v in value)
    if not isinstance(value, str):
        return bool(value)

    s = value.strip()
    if not s:
        return False

    placeholders = {"-", "\u2014", "\u2013", "_", "null", "none", "na", "n/a", "nan"}
    return s.lower() not in placeholders


def has_ground_truth(rows: list[dict[str, Any]]) -> bool:
    """Check whether any row has ground truth data."""
    for r in rows:
        if _has_real_value(r.get("relevant_passage")):
            return True
        if _has_real_value(r.get("target_context")):
            return True
    return False


# ---------------------------------------------------------------------------
# Input reading
# ---------------------------------------------------------------------------


def read_evaluation_input(input_path: Path) -> list[dict]:
    """Read evaluation input from CSV or JSON file.

    Normalizes column names from various formats into a unified schema:
    question, answer, relevant_passage, target_context.

    Args:
        input_path: Path to CSV or JSON file.

    Returns:
        List of normalized row dicts.

    Raises:
        FileNotFoundError: If input_path does not exist.
        ValueError: If CSV is missing a question column or JSON is not a list.
    """
    if not input_path.exists():
        raise FileNotFoundError(f"Input file {input_path} not found.")

    rows: list[dict] = []

    if input_path.suffix.lower() == ".json":
        with open(input_path, encoding="utf-8") as f:
            json_data = json.load(f)

        if not isinstance(json_data, list):
            raise ValueError("JSON file must contain a list of objects")

        for item in json_data:
            question = item.get("question") or item.get("user_input") or item.get("query")
            answer = item.get("answer") or item.get("response") or item.get("target")
            relevant = item.get("document") or item.get("documents") or item.get("relevant_passage")
            target_context = item.get("target_context") or item.get("reference_context")

            if question:
                rows.append(
                    {
                        "question": question,
                        "answer": answer,
                        "relevant_passage": relevant,
                        "target_context": target_context,
                    }
                )
    else:
        with open(input_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or []

            question_col = next(
                (c for c in fieldnames if c.lower() in ["question", "user_input", "query"]),
                "question",
            )
            answer_col = next(
                (
                    c
                    for c in fieldnames
                    if c.lower() in ["answer", "response", "target", "reference_answer"]
                ),
                "answer",
            )
            context_col = next(
                (
                    c
                    for c in fieldnames
                    if c.lower()
                    in ["relevant_passage", "relevant_passage_ids", "document", "documents"]
                ),
                "relevant_passage",
            )
            target_context_col = next(
                (c for c in fieldnames if c.lower() in ["target_context", "reference_context"]),
                None,
            )

            if question_col not in fieldnames:
                raise ValueError(f"Input CSV must have a question column. Found: {fieldnames}")

            for row in reader:
                rows.append(
                    {
                        "question": row.get(question_col),
                        "answer": row.get(answer_col),
                        "relevant_passage": row.get(context_col),
                        "target_context": row.get(target_context_col)
                        if target_context_col
                        else None,
                    }
                )

    return rows


# ---------------------------------------------------------------------------
# RAG service client
# ---------------------------------------------------------------------------


async def query_rag_system(
    client: httpx.AsyncClient,
    user_query: str,
    rag_service_url: str,
) -> dict:
    """Send a query to the RAG service /api/query/evaluation endpoint.

    Args:
        client: httpx async client.
        user_query: User question text.
        rag_service_url: Base URL of the RAG service.

    Returns:
        RAG response dict, or dict with 'error' key on failure.
    """
    base_url = rag_service_url.rstrip("/")
    url = f"{base_url}/api/query/evaluation"
    try:
        response = await client.post(
            url,
            headers={"Content-Type": "application/json"},
            json={"query": user_query},
        )
        if response.status_code == 200:
            return response.json()
        return {"error": response.text, "status_code": response.status_code}
    except Exception as e:
        return {"error": str(e), "status_code": 0}


# ---------------------------------------------------------------------------
# External evaluation service
# ---------------------------------------------------------------------------


async def call_evaluation_service(
    client: httpx.AsyncClient,
    evaluation_url: str,
    results: list[dict],
    output_dir: Path | None = None,
) -> list[dict]:
    """Send results to external evaluation service for generation metrics.

    The service expects a CSV file upload and returns CSV with added
    columns: faithfulness, answer_correctness, donkit_score.

    Args:
        client: httpx async client.
        evaluation_url: URL of the evaluation service.
        results: List of per-row result dicts.
        output_dir: Optional directory to save debug CSV files.

    Returns:
        Results list with evaluation metrics merged in.
    """
    logger.debug(f"Preparing {len(results)} results for evaluation service")
    eval_rows = []
    for r in results:
        if "error" in r:
            continue
        target_context_raw = r.get("_target_context_raw", [])
        if not isinstance(target_context_raw, list):
            target_context_raw = [target_context_raw] if target_context_raw else []

        eval_rows.append(
            {
                "query": r.get("question", ""),
                "generated_answer": r.get("answer", ""),
                "target": r.get("_target_answer", ""),
                "context": repr([]),
                "target_context": repr(target_context_raw),
            }
        )

    if not eval_rows:
        logger.debug("No valid rows to evaluate")
        return results

    output = io.StringIO()
    fieldnames = ["query", "generated_answer", "target", "context", "target_context"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(eval_rows)
    csv_content = output.getvalue().encode("utf-8")
    logger.debug(f"CSV content size: {len(csv_content)} bytes, {len(eval_rows)} rows")

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "evaluation_input.csv").write_bytes(csv_content)

    try:
        response = await client.post(
            evaluation_url,
            files={"file": ("dataset.csv", csv_content, "text/csv")},
            data={"format": "csv"},
            timeout=httpx.Timeout(600.0),
        )

        if response.status_code != 200:
            logger.error(f"Evaluation service error: {response.status_code} - {response.text}")
            return results

        response_csv = response.text
        if output_dir and response_csv:
            (output_dir / "evaluation_output.csv").write_text(response_csv, encoding="utf-8")

        reader = csv.DictReader(io.StringIO(response_csv))
        evaluated_rows = list(reader)

        eval_by_question = {
            (row.get("user_input") or row.get("query") or ""): row for row in evaluated_rows
        }

        for r in results:
            if "error" in r:
                continue
            question = r.get("question", "")
            if question in eval_by_question:
                eval_data = eval_by_question[question]
                r["_answer_accuracy"] = eval_data.get("answer_accuracy", "")
                r["_simple_criteria"] = eval_data.get("simple_criteria", "")
                r["_rubric_score"] = eval_data.get("rubric_score", "")
                r["_faithfulness"] = eval_data.get("faithfulness", "")
                r["_donkit_score"] = eval_data.get("donkit_score", "")

        return results

    except Exception as e:
        logger.error(f"Evaluation service call failed: {e}")
        return results


async def rerun_evaluation_from_csv(
    *,
    evaluation_url: str,
    input_csv_path: str | Path,
    output_csv_path: str | Path | None = None,
) -> dict:
    """Re-run evaluation service from a previously saved input CSV.

    Args:
        evaluation_url: URL of the evaluation service.
        input_csv_path: Path to the input CSV.
        output_csv_path: Path to save the output CSV. Defaults to sibling file.

    Returns:
        Dict with status, input_file, output_file or error.
    """
    input_path = Path(input_csv_path)
    if not input_path.exists():
        return {"error": f"Input CSV not found: {input_path}"}

    output_path = (
        Path(output_csv_path)
        if output_csv_path is not None
        else input_path.parent / "evaluation_output.csv"
    )

    csv_content = input_path.read_bytes()
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(600.0)) as client:
            response = await client.post(
                evaluation_url,
                files={"file": ("dataset.csv", csv_content, "text/csv")},
                data={"format": "csv"},
            )

        if response.status_code != 200:
            return {
                "error": "Evaluation service error",
                "status_code": response.status_code,
                "detail": response.text,
            }

        output_path.write_text(response.text, encoding="utf-8")
        return {
            "status": "success",
            "input_file": str(input_path),
            "output_file": str(output_path),
        }
    except Exception:
        raise


# ---------------------------------------------------------------------------
# Aggregate metrics
# ---------------------------------------------------------------------------


def compute_aggregate_metrics(results: list[dict]) -> dict[str, float | None]:
    """Compute aggregate metrics from per-row results.

    Args:
        results: List of per-row result dicts with _precision, _recall, etc.

    Returns:
        Dict with mean_accuracy, mean_precision, mean_recall, and
        optional generation metrics.
    """
    total_acc = sum(r.get("_accuracy", 0) for r in results if "_accuracy" in r)
    total_prec = sum(r.get("_precision", 0) for r in results if "_precision" in r)
    total_rec = sum(r.get("_recall", 0) for r in results if "_recall" in r)
    count = len([r for r in results if "_accuracy" in r])

    def _safe_mean(vals: list[float]) -> float | None:
        return sum(vals) / len(vals) if vals else None

    return {
        "mean_accuracy": total_acc / count if count > 0 else 0,
        "mean_precision": total_prec / count if count > 0 else 0,
        "mean_recall": total_rec / count if count > 0 else 0,
        "mean_answer_accuracy": _safe_mean(
            [float(r["_answer_accuracy"]) for r in results if r.get("_answer_accuracy")]
        ),
        "mean_simple_criteria": _safe_mean(
            [float(r["_simple_criteria"]) for r in results if r.get("_simple_criteria")]
        ),
        "mean_rubric_score": _safe_mean(
            [float(r["_rubric_score"]) for r in results if r.get("_rubric_score")]
        ),
        "mean_faithfulness": _safe_mean(
            [float(r["_faithfulness"]) for r in results if r.get("_faithfulness")]
        ),
        "mean_donkit_score": _safe_mean(
            [float(r["_donkit_score"]) for r in results if r.get("_donkit_score")]
        ),
    }


# ---------------------------------------------------------------------------
# Main evaluator
# ---------------------------------------------------------------------------


class RagEvaluator:
    """Batch RAG evaluation engine.

    Reads questions, queries RAG service, computes metrics,
    optionally calls external evaluation service, saves CSV results.
    """

    @staticmethod
    async def evaluate_batch(
        *,
        input_path: str | Path,
        project_id: str,
        rag_service_url: str = "http://localhost:8000",
        output_csv_path: str | Path | None = None,
        evaluation_service_url: str | None = None,
        max_concurrent: int = 5,
        max_questions: int | None = None,
    ) -> dict:
        """Run batch evaluation.

        Args:
            input_path: Path to CSV or JSON with evaluation questions.
            project_id: Project ID for organizing output files.
            rag_service_url: Base URL of the RAG service.
            output_csv_path: Path to save results CSV.
            evaluation_service_url: Optional external evaluation service URL.
            max_concurrent: Max concurrent requests to RAG service.
            max_questions: Limit number of questions (for debugging).

        Returns:
            Dict with status, metrics, timing, output_file.
        """
        path = Path(input_path)

        # Determine output path
        if output_csv_path:
            output = Path(output_csv_path).resolve()
        else:
            output = Path(f"projects/{project_id}/evaluation/results.csv").resolve()

        # Read input
        try:
            rows = read_evaluation_input(path)
        except (FileNotFoundError, ValueError) as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": f"Failed to read input file: {str(e)}"}

        # Determine benchmark mode
        benchmark_mode = not has_ground_truth(rows)
        if benchmark_mode and output_csv_path is None:
            output = Path(f"projects/{project_id}/evaluation/result.csv").resolve()

        # Limit questions
        if max_questions is not None and max_questions > 0:
            rows = rows[:max_questions]

        # Process rows concurrently
        semaphore = asyncio.Semaphore(max_concurrent)

        async def _process_row(row: dict) -> dict | None:
            async with semaphore:
                question = row.get("question")
                if not question:
                    return None

                try:
                    async with httpx.AsyncClient(timeout=60.0) as client:
                        start_time = time.time()
                        rag_response = await query_rag_system(client, question, rag_service_url)
                        rag_response_time = time.time() - start_time

                    if "error" in rag_response:
                        return {
                            "question": question,
                            "error": rag_response["error"],
                            "status_code": rag_response.get("status_code"),
                        }

                    generated_answer, retrieved_ids, chunks = extract_answer_and_sources(
                        rag_response
                    )

                    relevant_ids: list[str] = []
                    metrics = {"precision": 0.0, "recall": 0.0, "accuracy": 0.0}
                    if not benchmark_mode:
                        relevant_passage_raw = row.get("relevant_passage", "")
                        relevant_ids = DocumentNormalizer.extract_documents(relevant_passage_raw)
                        metrics = RAGMetrics.compute_retrieval_metrics(retrieved_ids, relevant_ids)

                    docs_for_csv = [doc.replace(".json", ".pdf") for doc in retrieved_ids]

                    if benchmark_mode:
                        return {
                            "question": question,
                            "answer": generated_answer,
                            "document": json.dumps(docs_for_csv, ensure_ascii=False),
                        }

                    target_context_raw = row.get("target_context")
                    if target_context_raw:
                        try:
                            target_context_list = ast.literal_eval(target_context_raw)
                            if not isinstance(target_context_list, list):
                                target_context_list = [target_context_raw]
                        except (ValueError, SyntaxError):
                            target_context_list = [target_context_raw]
                    else:
                        target_context_list = []

                    return {
                        "question": question,
                        "docs": json.dumps(docs_for_csv, ensure_ascii=False),
                        "chunks": json.dumps(chunks, ensure_ascii=False),
                        "answer": generated_answer,
                        "_target_answer": row.get("answer"),
                        "_relevant_context": relevant_ids,
                        "_retrieved_context": retrieved_ids,
                        "_chunks_raw": chunks,
                        "_target_context_raw": target_context_list,
                        "_precision": metrics["precision"],
                        "_recall": metrics["recall"],
                        "_accuracy": metrics["accuracy"],
                        "_rag_response_time": rag_response_time,
                    }
                except Exception as e:
                    return {"question": question, "error": str(e)}

        rag_start_time = time.time()
        tasks = [_process_row(row) for row in rows]
        raw_results = await asyncio.gather(*tasks)
        rag_total_time = time.time() - rag_start_time

        valid_results = [r for r in raw_results if r]

        # Benchmark mode — simplified output
        if benchmark_mode:
            return RagEvaluator._save_benchmark_results(valid_results, output, rag_total_time)

        # Call external evaluation service if configured
        eval_total_time = 0.0
        if evaluation_service_url:
            eval_start_time = time.time()
            async with httpx.AsyncClient() as eval_client:
                valid_results = await call_evaluation_service(
                    eval_client,
                    evaluation_service_url,
                    valid_results,
                    output_dir=output.parent,
                )
            eval_total_time = time.time() - eval_start_time

        # Aggregate metrics
        aggregates = compute_aggregate_metrics(valid_results)

        rag_times = [
            r.get("_rag_response_time", 0) for r in valid_results if "_rag_response_time" in r
        ]
        avg_rag_response_time = sum(rag_times) / len(rag_times) if rag_times else 0

        # Save CSV
        try:
            output.parent.mkdir(parents=True, exist_ok=True)
            with open(output, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=["question", "docs", "chunks", "answer"],
                    extrasaction="ignore",
                )
                writer.writeheader()
                writer.writerows(valid_results)

            return {
                "status": "success",
                "processed_rows": len(valid_results),
                "output_file": str(output),
                "metrics": aggregates,
                "timing": {
                    "rag_total_time_sec": round(rag_total_time, 2),
                    "avg_rag_response_time_sec": round(avg_rag_response_time, 3),
                    "evaluation_time_sec": round(eval_total_time, 2),
                },
            }
        except Exception as e:
            return {"error": "Failed to save results", "detail": str(e)}

    @staticmethod
    def _save_benchmark_results(
        results: list[dict],
        output_path: Path,
        rag_total_time: float,
    ) -> dict:
        """Save benchmark-mode results (no ground truth)."""
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=["question", "answer", "document"],
                    extrasaction="ignore",
                )
                writer.writeheader()
                writer.writerows(results)

            rag_times = [
                r.get("_rag_response_time", 0)
                for r in results
                if r.get("_rag_response_time") is not None
            ]
            avg_rag_response_time = sum(rag_times) / len(rag_times) if rag_times else 0

            return {
                "status": "success",
                "mode": "benchmark",
                "processed_rows": len(results),
                "output_file": str(output_path),
                "timing": {
                    "rag_total_time_sec": round(rag_total_time, 2),
                    "avg_rag_response_time_sec": round(avg_rag_response_time, 3),
                },
            }
        except Exception as e:
            return {"error": "Failed to save results", "detail": str(e)}
