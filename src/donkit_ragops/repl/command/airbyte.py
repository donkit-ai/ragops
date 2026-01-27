from donkit_ragops.repl import CommandResult
from donkit_ragops.repl import ReplContext
from donkit_ragops.repl.commands import ReplCommand
from donkit_ragops.ui import StyleName
from donkit_ragops.ui.styles import styled_text


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
        return CommandResult(
            styled_messages=[styled_text((StyleName.WARNING, "Hello from Airbyte!"))]
        )
