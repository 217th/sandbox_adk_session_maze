"""Core maze logic for validating moves and describing the grid."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple


DIRECTIONS: Dict[str, Tuple[int, int]] = {
    "north": (0, -1),
    "south": (0, 1),
    "west": (-1, 0),
    "east": (1, 0),
}


@dataclass(frozen=True)
class MoveResult:
    """Represents the outcome of a move attempt."""

    success: bool
    status: str
    new_position: Tuple[int, int] | None
    message: str = ""


class MazeEngine:
    """Pure game logic for the 3x3 maze."""

    GRID_SIZE = 3
    START = (0, 0)
    GOAL = (2, 2)
    WALLS = {(1, 0), (1, 1)}

    def attempt_move(self, position: Tuple[int, int], direction: str) -> MoveResult:
        """Return the result of attempting to move in ``direction``."""
        normalized_direction = direction.strip().lower()
        if normalized_direction not in DIRECTIONS:
            return MoveResult(
                success=False,
                status="invalid_direction",
                new_position=None,
                message="Неизвестное направление.",
            )

        dx, dy = DIRECTIONS[normalized_direction]
        target = (position[0] + dx, position[1] + dy)

        if not self._is_within_bounds(target):
            return MoveResult(
                success=False,
                status="out_of_bounds",
                new_position=None,
                message="Вы упрётесь в край сетки.",
            )

        if target in self.WALLS:
            return MoveResult(
                success=False,
                status="blocked",
                new_position=None,
                message="На пути стена.",
            )

        return MoveResult(success=True, status="success", new_position=target)

    def describe_surroundings(self, position: Tuple[int, int]) -> Dict[str, str]:
        """Return availability of moves for each direction."""
        description: Dict[str, str] = {}
        for direction in DIRECTIONS:
            description[direction] = self._classify_neighbor(position, direction)
        return description

    def is_goal(self, position: Tuple[int, int]) -> bool:
        return position == self.GOAL

    def _is_within_bounds(self, position: Tuple[int, int]) -> bool:
        x, y = position
        return 0 <= x < self.GRID_SIZE and 0 <= y < self.GRID_SIZE

    def _classify_neighbor(self, position: Tuple[int, int], direction: str) -> str:
        """Return 'free', 'wall', or 'out_of_bounds' for the adjacence."""
        dx, dy = DIRECTIONS[direction]
        target = (position[0] + dx, position[1] + dy)
        if not self._is_within_bounds(target):
            return "out_of_bounds"
        if target in self.WALLS:
            return "wall"
        return "free"
