"""Unit tests for the Maze Agent PRD requirements."""

from maze_agent.agent_handler import AgentHandler, BLOCKED_FLASH_MESSAGE
from maze_agent.session_manager import SessionManager


class FakeSession:
    """Simple stand-in for google.adk.sessions.Session."""

    def __init__(self):
        self.state = {}
        self.events = []  # mirrors ADK conversation events


def test_move_south_updates_state():
    handler = AgentHandler()
    session = FakeSession()

    response, delta = handler.process_turn("go south", session)

    assert session.state["player_position"] == {"x": 0, "y": 1}
    assert response.startswith("Шаг успешен")
    assert delta["player_position"] == {"x": 0, "y": 1}


def test_state_unchanged_on_blocked_move():
    handler = AgentHandler()
    session = FakeSession()

    response, delta = handler.process_turn("go east", session)

    assert session.state["player_position"] == {"x": 0, "y": 0}
    assert session.state["_maze_event_log"][-1]["parameters"]["result"] == "blocked"
    assert "На пути стена" in response
    assert BLOCKED_FLASH_MESSAGE in response
    assert "_maze_event_log" in delta
    assert "_flash_buffer" in delta


def test_three_failures_trigger_sarcasm():
    handler = AgentHandler()
    session = FakeSession()

    for _ in range(2):
        handler.process_turn("go east", session)

    response, delta = handler.process_turn("go east", session)

    log = session.state["_maze_event_log"]
    assert all(event["parameters"]["result"] == "blocked" for event in log[-3:])
    assert "Кажется, стена вам нравится" in response
    assert "_maze_event_log" in delta
    assert BLOCKED_FLASH_MESSAGE in response


def test_flash_ephemeral_storage():
    session = FakeSession()
    manager = SessionManager(session)

    manager.add_flash("notifications", "Test Msg")
    assert session.state["_flash_buffer"]["notifications"] == ["Test Msg"]

    messages = manager.consume_flash("notifications")
    assert messages == ["Test Msg"]
    assert session.state["_flash_buffer"]["notifications"] == []


def test_flash_isolation_between_turns():
    handler = AgentHandler()
    session = FakeSession()

    response1, _ = handler.process_turn("go east", session)
    assert BLOCKED_FLASH_MESSAGE in response1

    response2, _ = handler.process_turn("look", session)
    assert BLOCKED_FLASH_MESSAGE not in response2
    assert session.state["_flash_buffer"]["notifications"] == []
