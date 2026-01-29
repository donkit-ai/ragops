from uuid import UUID

from donkit_ragops.repl.base import ReplContext
from donkit_ragops.repl.commands import CommandResult, ReplCommand
from donkit_ragops.ui.styles import StyleName, styled_text


class AirbyteCommand(ReplCommand):
    """Enables Airbyte integration."""

    @property
    def name(self) -> str:
        return "airbyte"

    @property
    def aliases(self) -> list[str]:
        return ["ab"]

    @property
    def description(self) -> str:
        return "Connect to Airbyte"

    async def execute(self, context: ReplContext) -> CommandResult:
        if not context.api_client:
            return CommandResult(
                styled_messages=[
                    styled_text(
                        (StyleName.ERROR, "Airbyte integration is only available in server mode.")
                    )  # fmt: skip
                ]
            )

        if not context.project_id:
            return CommandResult(
                styled_messages=[
                    styled_text(
                        (StyleName.ERROR, "No active project. Please start a session first.")
                    )
                ]
            )

        try:
            async with context.api_client:
                response = await context.api_client.create_airbyte_sink(
                    project_id=UUID(context.project_id),
                    name="Airbyte Sink",
                )

            return CommandResult(
                styled_messages=[
                    styled_text((StyleName.SUCCESS, "Airbyte sink created!")),
                    styled_text((StyleName.INFO, f"Webhook URL: {response.webhook_url}")),
                    styled_text((StyleName.DIM, "Configure this URL in your Airbyte connection.")),
                ]
            )
        except Exception as e:
            return CommandResult(
                styled_messages=[
                    styled_text((StyleName.ERROR, f"Failed to create Airbyte sink: {e}"))
                ]
            )
