"""Implements the Maze agent turn processing."""

from __future__ import annotations

import json
import logging
from typing import Any, Tuple

from .engine import DIRECTIONS, MazeEngine
from .session_manager import SessionManager

RUSSIAN_DIRECTIONS = {
    "north": "север",
    "south": "юг",
    "east": "восток",
    "west": "запад",
}

BLOCKED_FLASH_MESSAGE = "Удар был болезненным!"


class AgentHandler:
    """Process a user command within the Maze session."""

    def __init__(self, engine: MazeEngine | None = None, sarcasm_threshold: int = 3) -> None:
        self._engine = engine or MazeEngine()
        self._sarcasm_threshold = sarcasm_threshold
        self._logger = logging.getLogger("maze_agent.handler")

    def process_turn(self, user_input: str, session: Any) -> tuple[str, dict]:
        command = (user_input or "").strip().lower()
        self._logger.info("Команда пользователя: %s", user_input.strip() if user_input else "<пусто>")
        session_manager = SessionManager(session)
        state = session_manager.get_state()
        position = self._tuple_from_state(state["player_position"])

        if not command:
            response = "Используйте команды 'go <direction>', 'look' или 'history'."
        elif command == "look":
            description = self._describe_position(position)
            session_manager.add_event(
                {"action_type": "LOOK", "parameters": {"description": description}}
            )
            response = description
        elif command == "history":
            events = session_manager.get_all_events()
            session_manager.add_event(
                {
                    "action_type": "SYSTEM_MSG",
                    "parameters": {"message": "history_requested", "count": len(events)},
                }
            )
            response = json.dumps(events, ensure_ascii=False, indent=2)
        elif command.startswith("go "):
            direction = command.split(" ", 1)[1].strip()
            response = self._handle_move(direction, position, state, session_manager)
        else:
            session_manager.add_event(
                {
                    "action_type": "SYSTEM_MSG",
                    "parameters": {"message": "unknown_command", "command": command},
                }
            )
            response = "Не понимаю команду. Доступно: go <north|south|east|west>, look, history."

        response = self._apply_flash_messages(response, session_manager)
        delta = session_manager.consume_state_delta()
        return response, delta

    def _handle_move(
        self,
        direction: str,
        position: Tuple[int, int],
        state: dict,
        session_manager: SessionManager,
    ) -> str:
        move_result = self._engine.attempt_move(position, direction)
        self._logger.info(
            "Попытка шага: направление=%s, результат=%s",
            direction,
            move_result.status,
        )
        event = session_manager.add_event(
            {
                "action_type": "MOVE_ATTEMPT",
                "parameters": {
                    "direction": direction,
                    "result": move_result.status,
                },
            }
        )

        if move_result.success and move_result.new_position:
            new_x, new_y = move_result.new_position
            current_status = session_manager.get_state().get("game_status", "active")
            next_status = (
                "won"
                if self._engine.is_goal(move_result.new_position)
                else current_status
            )
            session_manager.update_state(
                {
                    "player_position": {"x": new_x, "y": new_y},
                    "game_status": next_status,
                }
            )
            position = move_result.new_position
        else:
            position = self._tuple_from_state(state["player_position"])

        if move_result.success and move_result.new_position:
            self._logger.info(
                "Шаг выполнен: новая позиция=%s", self._format_position(move_result.new_position)
            )
        else:
            if move_result.status in {"blocked", "out_of_bounds"}:
                session_manager.add_flash("notifications", BLOCKED_FLASH_MESSAGE)

        response = self._compose_move_response(move_result, position, session_manager)

        # keep reference to event to avoid lint warnings (future use)
        _ = event
        return response

    def _compose_move_response(
        self,
        move_result,
        position: Tuple[int, int],
        session_manager: SessionManager,
    ) -> str:
        state = session_manager.get_state()
        sarcasm = self._sarcasm_needed(session_manager)

        base_description = self._describe_position(position)

        if move_result.success:
            if state.get("game_status") == "won":
                won_msg = "Вы добрались до цели (2,2). Поздравляю!"
                return f"{won_msg} {base_description}"
            return f"Шаг успешен. Текущая позиция: {self._format_position(position)}. {base_description}"

        failure_intro = move_result.message or "Ход невозможен."
        status_suffix = ""
        if sarcasm:
            status_suffix = (
                " Кажется, стена вам нравится. Может, попробуете другую сторону или команду 'look'?"
            )
        return f"{failure_intro} Вы всё ещё в {self._format_position(position)}. {base_description}{status_suffix}"

    def _apply_flash_messages(self, response: str, session_manager: SessionManager) -> str:
        flash_sections: list[str] = []
        notifications = session_manager.consume_flash("notifications")
        if notifications:
            flash_sections.append(" ".join(notifications))
        errors = session_manager.consume_flash("errors")
        if errors:
            flash_sections.append(" ".join(errors))
        if flash_sections:
            return f"{response} {' '.join(flash_sections)}"
        return response

    def _describe_position(self, position: Tuple[int, int]) -> str:
        description = [f"Вы находитесь в {self._format_position(position)}."]
        surroundings = self._engine.describe_surroundings(position)
        for direction, state in surroundings.items():
            dir_label = RUSSIAN_DIRECTIONS[direction]
            if state == "free":
                description.append(f"Путь на {dir_label} свободен.")
            elif state == "wall":
                description.append(f"На {dir_label} стоит стена.")
            else:
                description.append(f"На {dir_label} граница сетки.")
        return " ".join(description)

    def _sarcasm_needed(self, session_manager: SessionManager) -> bool:
        recent = session_manager.get_recent_events(self._sarcasm_threshold)
        if len(recent) < self._sarcasm_threshold:
            return False
        bad_statuses = {"blocked", "out_of_bounds"}
        return all(
            event.get("action_type") == "MOVE_ATTEMPT"
            and event.get("parameters", {}).get("result") in bad_statuses
            for event in recent
        )

    def _tuple_from_state(self, position_state: dict) -> Tuple[int, int]:
        return position_state["x"], position_state["y"]

    def _format_position(self, position: Tuple[int, int]) -> str:
        return f"({position[0]},{position[1]})"
