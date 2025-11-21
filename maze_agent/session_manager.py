"""Utilities for interacting with the ADK session container.

**Подробное объяснение:**
- `DEFAULT_STATE` описывает начальное состояние: игрок в `(0,0)`, `game_status="active"`, отдельный журнал `_maze_event_log` и flash-буфер `_flash_buffer`.
- `SessionManager.__init__` принимает ADK-сессию и создаёт `_state_delta`, который собирает все изменения состояния, чтобы потом выдать их наружу и передать в `EventActions.state_delta`.
- `get_state` гарантирует базовые ключи: если в `session.state` ещё нет обязательных значений, они создаются и тут же записываются в `_state_delta`.
- `update_state` принимает фрагмент для обновления, логирует “Было/Стало” и отмечает каждую пару ключ/значение в `_state_delta`.
- `add_event` добавляет запись в `_maze_event_log`, присваивает timestamp и фиксирует обновление журнала в `_state_delta`.
- Flash-методы `add_flash`/`consume_flash` управляют одноразовыми уведомлениями в `_flash_buffer`, который очищается сразу после чтения.
- `get_all_events` / `get_recent_events` читают журнал из `session.state`, не трогая ADK `session.events`.
- `clear_events` используется в тестах: очищает `_maze_event_log` и заносит изменение в `_state_delta`.
- `_event_log` инициализирует список событий, если его ещё не было, и сразу помечает delta.
- `_record_state_change` / `_record_state_change_bulk` обновляют `_state_delta` при любой мутации состояния.
- `consume_state_delta` возвращает накопленный delta dict и очищает буфер; delta уходит в `EventActions.state_delta`, иначе изменения бы терялись между ходами.
- `_timestamp` выдаёт ISO-время в UTC для журнала событий.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
from copy import deepcopy
from typing import Any, Dict, List

_EVENTS_KEY = "_maze_event_log"
_FLASH_KEY = "_flash_buffer"

LOGGER = logging.getLogger("maze_agent.session")

DEFAULT_STATE = {
    "player_position": {"x": 0, "y": 0},
    "game_status": "active",
    _FLASH_KEY: {"notifications": [], "errors": []},
}


class SessionManager:
    """Wraps the ADK ``session`` object and enforces defaults."""

    def __init__(self, session: Any) -> None:
        if session is None:
            raise ValueError("SessionManager requires a session instance.")
        self._session = session
        self._state_delta: Dict[str, Any] = {}

    def get_state(self) -> Dict[str, Any]:
        state = getattr(self._session, "state", None)
        if state is None:
            state = {}
            self._session.state = state

        if "player_position" not in state:
            state["player_position"] = DEFAULT_STATE["player_position"].copy()
            self._record_state_change("player_position", state["player_position"])
        if "game_status" not in state:
            state["game_status"] = DEFAULT_STATE["game_status"]
            self._record_state_change("game_status", state["game_status"])
        if _FLASH_KEY not in state:
            state[_FLASH_KEY] = self._new_flash_buffer()
            self._record_state_change(_FLASH_KEY, state[_FLASH_KEY])
        return state

    def update_state(self, new_data: Dict[str, Any]) -> None:
        state = self.get_state()
        before = json.dumps(state, ensure_ascii=False, sort_keys=True)
        state.update(new_data)
        self._record_state_change_bulk(new_data)
        LOGGER.info(
            "Состояние сессии обновлено. Было: %s | Стало: %s",
            before,
            json.dumps(state, ensure_ascii=False, sort_keys=True),
        )

    def add_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        events = self._event_log()
        event = {
            "timestamp": self._timestamp(),
            **event_data,
        }
        events.append(event)
        self._record_state_change(_EVENTS_KEY, list(events))
        return event

    def get_all_events(self) -> List[Dict[str, Any]]:
        return list(self._event_log())

    def get_recent_events(self, count: int) -> List[Dict[str, Any]]:
        events = self._event_log()
        if count <= 0:
            return []
        return events[-count:]

    def clear_events(self) -> None:
        """Helper for tests to reset the event log."""
        self.get_state()[_EVENTS_KEY] = []
        self._record_state_change(_EVENTS_KEY, [])

    def _event_log(self) -> List[Dict[str, Any]]:
        state = self.get_state()
        events = state.get(_EVENTS_KEY)
        if events is None:
            events = []
            state[_EVENTS_KEY] = events
            self._record_state_change(_EVENTS_KEY, events)
        return events

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    def add_flash(self, category: str, message: str) -> None:
        buffer = self._flash_buffer()
        bucket = buffer.setdefault(category, [])
        bucket.append(message)
        self._record_state_change(_FLASH_KEY, buffer)

    def consume_flash(self, category: str) -> List[str]:
        buffer = self._flash_buffer()
        bucket = buffer.setdefault(category, [])
        messages = list(bucket)
        if messages:
            buffer[category] = []
            self._record_state_change(_FLASH_KEY, buffer)
        return messages

    def _record_state_change(self, key: str, value: Any) -> None:
        self._state_delta[key] = deepcopy(value)

    def _record_state_change_bulk(self, changes: Dict[str, Any]) -> None:
        for key, value in changes.items():
            self._record_state_change(key, value)

    def consume_state_delta(self) -> Dict[str, Any]:
        delta = dict(self._state_delta)
        self._state_delta.clear()
        return delta

    def _flash_buffer(self) -> Dict[str, List[str]]:
        state = self.get_state()
        buffer = state.get(_FLASH_KEY)
        if buffer is None:
            buffer = self._new_flash_buffer()
            state[_FLASH_KEY] = buffer
            self._record_state_change(_FLASH_KEY, buffer)
        return buffer

    def _new_flash_buffer(self) -> Dict[str, List[str]]:
        return {
            "notifications": [],
            "errors": [],
        }
