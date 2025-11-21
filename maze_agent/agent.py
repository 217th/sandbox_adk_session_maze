"""ADK entrypoint exposing the Maze agent."""

from __future__ import annotations

from typing import AsyncGenerator, ClassVar

from google.genai import types

from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.base_agent_config import BaseAgentConfig
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions

from .agent_handler import AgentHandler


class MazeAdkAgent(BaseAgent):
    """Minimal BaseAgent wrapper around the Maze AgentHandler."""

    config_type: ClassVar[type[BaseAgentConfig]] = BaseAgentConfig

    def __init__(self, handler: AgentHandler | None = None):
        super().__init__(
            name="maze_agent",
            description="Управляет перемещением игрока по сетке 3x3, отслеживая состояние и историю.",
        )
        self._handler = handler or AgentHandler()

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        user_text = self._extract_user_text(ctx.user_content)
        response_text, state_delta = self._handler.process_turn(user_text, ctx.session)
        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            content=types.Content(
                role="assistant", parts=[types.Part(text=response_text)]
            ),
            actions=EventActions(state_delta=state_delta or None),
        )

    def _extract_user_text(self, content: types.Content | None) -> str:
        if not content or not content.parts:
            return ""
        pieces = [part.text for part in content.parts if part.text]
        return "\n".join(pieces).strip()


root_agent = MazeAdkAgent()
