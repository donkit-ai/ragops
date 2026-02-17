"""Tests for rag_builder.evaluation.evaluator."""

import csv
import json
from pathlib import Path

import pytest

from donkit_ragops.rag_builder.evaluation.evaluator import (
    _has_real_value,
    compute_aggregate_metrics,
    extract_answer_and_sources,
    has_ground_truth,
    read_evaluation_input,
)


class TestExtractAnswerAndSources:
    def test_basic(self):
        resp = {"answer": "hello", "context": "doc1.json, doc2.json", "chunks": ["c1", "c2"]}
        answer, ids, chunks = extract_answer_and_sources(resp)
        assert answer == "hello"
        assert ids == ["doc1.json", "doc2.json"]
        assert chunks == ["c1", "c2"]

    def test_context_as_list(self):
        resp = {"answer": "hi", "context": ["a", "b"], "chunks": []}
        _, ids, _ = extract_answer_and_sources(resp)
        assert ids == ["a", "b"]

    def test_empty_response(self):
        answer, ids, chunks = extract_answer_and_sources({})
        assert answer == ""
        assert ids == []
        assert chunks == []

    def test_chunks_not_list(self):
        resp = {"answer": "x", "chunks": "single"}
        _, _, chunks = extract_answer_and_sources(resp)
        assert chunks == ["single"]

    def test_chunks_none(self):
        resp = {"answer": "x", "chunks": None}
        _, _, chunks = extract_answer_and_sources(resp)
        assert chunks == []

    def test_context_not_string_or_list(self):
        resp = {"answer": "x", "context": 123}
        _, ids, _ = extract_answer_and_sources(resp)
        assert ids == []


class TestHasRealValue:
    def test_none(self):
        assert _has_real_value(None) is False

    def test_empty_string(self):
        assert _has_real_value("") is False
        assert _has_real_value("  ") is False

    def test_placeholders(self):
        for p in ["-", "_", "null", "None", "NA", "n/a", "nan", "\u2014", "\u2013"]:
            assert _has_real_value(p) is False, f"Failed for placeholder: {p}"

    def test_real_values(self):
        assert _has_real_value("doc1.pdf") is True
        assert _has_real_value("some text") is True
        assert _has_real_value(42) is True

    def test_list_with_real(self):
        assert _has_real_value(["doc1.pdf"]) is True

    def test_list_all_empty(self):
        assert _has_real_value([None, "", "-"]) is False


class TestHasGroundTruth:
    def test_with_relevant_passage(self):
        rows = [{"relevant_passage": "doc1.pdf"}]
        assert has_ground_truth(rows) is True

    def test_with_target_context(self):
        rows = [{"target_context": "some context"}]
        assert has_ground_truth(rows) is True

    def test_no_ground_truth(self):
        rows = [{"relevant_passage": None, "target_context": "-"}]
        assert has_ground_truth(rows) is False

    def test_empty(self):
        assert has_ground_truth([]) is False


class TestReadEvaluationInput:
    def test_read_json(self, tmp_path):
        data = [
            {"question": "Q1", "answer": "A1", "document": "doc1.pdf"},
            {"question": "Q2", "answer": "A2", "document": "doc2.pdf"},
        ]
        f = tmp_path / "eval.json"
        f.write_text(json.dumps(data))
        rows = read_evaluation_input(f)
        assert len(rows) == 2
        assert rows[0]["question"] == "Q1"
        assert rows[0]["relevant_passage"] == "doc1.pdf"

    def test_read_json_alternative_keys(self, tmp_path):
        data = [{"user_input": "Q1", "response": "A1", "relevant_passage": "d1"}]
        f = tmp_path / "eval.json"
        f.write_text(json.dumps(data))
        rows = read_evaluation_input(f)
        assert rows[0]["question"] == "Q1"
        assert rows[0]["answer"] == "A1"

    def test_read_csv(self, tmp_path):
        f = tmp_path / "eval.csv"
        with open(f, "w", newline="") as fp:
            writer = csv.DictWriter(fp, fieldnames=["question", "answer", "relevant_passage"])
            writer.writeheader()
            writer.writerow({"question": "Q1", "answer": "A1", "relevant_passage": "d1"})
        rows = read_evaluation_input(f)
        assert len(rows) == 1
        assert rows[0]["question"] == "Q1"

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            read_evaluation_input(Path("/nonexistent/file.json"))

    def test_json_not_list(self, tmp_path):
        f = tmp_path / "eval.json"
        f.write_text('{"not": "a list"}')
        with pytest.raises(ValueError, match="list"):
            read_evaluation_input(f)

    def test_csv_missing_question_col(self, tmp_path):
        f = tmp_path / "eval.csv"
        with open(f, "w", newline="") as fp:
            writer = csv.DictWriter(fp, fieldnames=["answer", "document"])
            writer.writeheader()
            writer.writerow({"answer": "A1", "document": "d1"})
        with pytest.raises(ValueError, match="question column"):
            read_evaluation_input(f)


class TestComputeAggregateMetrics:
    def test_basic(self):
        results = [
            {"_accuracy": 1.0, "_precision": 0.8, "_recall": 1.0},
            {"_accuracy": 0.0, "_precision": 0.5, "_recall": 0.5},
        ]
        agg = compute_aggregate_metrics(results)
        assert agg["mean_accuracy"] == 0.5
        assert abs(agg["mean_precision"] - 0.65) < 1e-9
        assert agg["mean_recall"] == 0.75

    def test_with_generation_metrics(self):
        results = [
            {"_accuracy": 1.0, "_precision": 1.0, "_recall": 1.0, "_faithfulness": "0.9"},
            {"_accuracy": 1.0, "_precision": 1.0, "_recall": 1.0, "_faithfulness": "0.7"},
        ]
        agg = compute_aggregate_metrics(results)
        assert agg["mean_faithfulness"] == 0.8

    def test_empty(self):
        agg = compute_aggregate_metrics([])
        assert agg["mean_accuracy"] == 0
        assert agg["mean_faithfulness"] is None

    def test_no_generation_metrics(self):
        results = [{"_accuracy": 1.0, "_precision": 1.0, "_recall": 1.0}]
        agg = compute_aggregate_metrics(results)
        assert agg["mean_donkit_score"] is None
        assert agg["mean_answer_accuracy"] is None
