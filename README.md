# ADK Maze Agent

Учебный агент, демонстрирующий работу с состоянием (`session.state`), flash-данными и журналом событий (`session.events`) в Google ADK: https://google.github.io/adk-docs/. 

Пользователь перемещается по сетке 3×3, избегает стен и фиксирует каждую попытку хода. Проект показывает, как отделять:

- **State (mutable):** положение игрока и статус игры.
- **Events (append-only):** журнал действий пользователя.
- **Flash (read-once):** одноразовые уведомления, которые должны появиться только в следующем ответе.

## Игровые правила

- Размер сетки: 3×3, координаты `0..2`.
- Старт: `(0,0)`, цель: `(2,2)`.
- Стены: `(1,0)` и `(1,1)`.
- Команды: `go <north|south|east|west>`, `look`, `history`.
- Три последовательных неудачных попытки хода включают саркастический тон.
- Блокированный ход добавляет flash-сообщение “Удар был болезненным!”, которое автоматически исчезает после следующего ответа.

## Структура

- `maze_agent/engine.py` — чистая логика лабиринта: проверка ходов, описание окружения, детекция цели.
- `maze_agent/session_manager.py` — обёртка над ADK `session`. Гарантирует наличие ключей (`player_position`, `game_status`, `_maze_event_log`, `_flash_buffer`), ведёт `_state_delta`, добавляет события и flash-сообщения, предоставляет `consume_state_delta()` для `EventActions.state_delta`.
- `maze_agent/agent_handler.py` — бизнес-логика. Парсит команды, вызывает `MazeEngine`, обновляет состояние/события/flash, проверяет “упрямство”, добавляет сарказм. Все ответы проходят через `_apply_flash_messages`, чтобы вывести одноразовые уведомления.
- `maze_agent/agent.py` — точка входа для ADK. `MazeAdkAgent` наследует `BaseAgent`, извлекает пользовательский текст из `InvocationContext`, вызывает `AgentHandler.process_turn()` и эмитит `Event` с `state_delta`.
- `tests/test_maze_agent.py` — pytest-набор: движение, блокировки, сарказм, flash-эфемерность и изоляция ходов.

## Состояние, события, flash

```bash
# session.state:
player_position -> текущая координата
game_status     -> 'active' или 'won'
_maze_event_log -> append-only журнал
_flash_buffer   -> {'notifications': [...], 'errors': [...]}
```

- `SessionManager.add_event()` сохраняет данные в `_maze_event_log` и сразу фиксирует delta.
- `SessionManager.add_flash()` записывает одноразовое сообщение (например, при ударе о стену).
- `SessionManager.consume_flash(category)` возвращает текущий список и очищает bucket.
- `AgentHandler.process_turn()` всегда завершает ход `session_manager.consume_state_delta()`, поэтому Runner получает полный `state_delta`.

## Интеграция с ADK Runner

`AgentHandler.process_turn` ожидает объект `session`, совместимый с `google.adk.sessions.Session`. ADK автоматически передаёт сессию через `InvocationContext`, поэтому `maze_agent/agent.py` создаёт `root_agent`, который достаёт пользовательский ввод и передаёт его в `AgentHandler`. Запустите демо:

```bash
adk web .
```

ADK найдёт `maze_agent/agent.py`, создаст Runner и позволит взаимодействовать через встроенный UI. В сессии данные делятся на:

- `session.state.player_position` / `session.state.game_status` — изменяемый слепок состояния.
- `session.state["_maze_event_log"]` — append-only журнал событий, который выводится командой `history`.
- `session.state["_flash_buffer"]` — одноразовые уведомления (`notifications`, `errors`). Агент добавляет сообщения при столкновениях и удаляет их сразу после вывода, поэтому они видны только в следующем ответе.

## Запуск тестов

```bash
pip install -e '.[dev]'
python -m pytest
```

Тесты покрывают требования PRD: изменение позиции, неизменность при блокировке, накопление событий, срабатывание сарказма и поведение flash-памяти (эфемерность и изоляция между ходами).
