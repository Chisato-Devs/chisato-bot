from __future__ import annotations

from random import shuffle
from typing import Optional, TYPE_CHECKING

from loguru import logger

from .enums import Symbol

Square = int

if TYPE_CHECKING:
    from disnake import Member


class Board:
    def __init__(self, players: list[Member | int | str], *, bid: int, size: int = 3) -> None:
        self.size: int = size
        self.p1_score: int = 0
        self.p2_score: int = 0

        self.bid = bid

        shuffle(players)
        self.player1 = players[0]
        self.player2 = players[1]

        self.squares: dict[[int, int], Square] = self.get_squares()
        self.table: list[Symbol] = self.get_table()
        self.win_conditions: list[list[Square]] = self.get_win_conditions()

        self.first_move: Symbol = Symbol.CIRCLE
        self.turn: Symbol = self.first_move

    def get_win_conditions(self) -> list[list[Square]]:
        rows, cols = self.get_rows_cols()
        diagonals = self.get_diagonals()
        return rows + cols + diagonals

    def get_squares(self) -> dict[[int, int], Square]:
        return {(r, c): r * self.size + c
                for r in range(self.size) for c in range(self.size)}

    def get_table(self) -> list[Symbol]:
        return [Symbol.EMPTY for _ in range(self.size ** 2)]

    def get_rows_cols(self) -> tuple:
        rows: list[list[Square]] = [[] for _ in range(self.size)]
        columns: list[list[Square]] = [[] for _ in range(self.size)]
        for index, square in self.squares.items():
            r, c = index
            rows[r].append(square)
            columns[c].append(square)
        return rows, columns

    def get_diagonals(self) -> list[list[Square]]:
        diagonals: list[list] = [[], []]
        i = 0
        j = self.size - 1
        for _ in range(self.size):
            diagonals[0].append(i)
            diagonals[1].append(j)
            i += self.size + 1
            j += self.size - 1
        return diagonals

    @property
    def empty_squares(self) -> list[Square]:
        return [
            square for square in self.squares.values() if self.is_empty(square)
        ]

    def reset(self) -> None:
        self.table = self.get_table()
        self.first_move = Symbol.CROSS if self.first_move == Symbol.CIRCLE else Symbol.CIRCLE
        self.turn = self.first_move

    def square_pos(self, square: Square) -> Optional[tuple[int, int]]:
        for pos, sq in self.squares.items():
            if sq == square:
                return pos
        return None

    def square_name(self, row: int, col: int) -> Square:
        return self.squares[(row, col)]

    def square_value(self, square: Square) -> Symbol:
        return self.table[square]

    def is_empty(self, square: Square) -> bool:
        return self.table[square] == Symbol.EMPTY

    def get_connection(self) -> list[Square]:
        for row in self.win_conditions:
            checklist = []
            for square in row:
                if self.is_empty(square):
                    continue
                checklist.append(self.square_value(square))
            if len(checklist) == self.size and len(set(checklist)) == 1:
                return row
        return []

    def is_draw(self) -> bool:
        if len(self.empty_squares) == 0 and len(self.get_connection()) == 0:
            return True
        return False

    def winner(self) -> Optional[Member | int | str]:
        connection = self.get_connection()
        if len(connection) == 0:
            return None
        elif self.square_value(connection[0]) == Symbol.CIRCLE:
            return self.player1
        else:
            return self.player2

    def is_gameover(self) -> bool:
        return self.winner() is not None or self.is_draw()

    def _update(self) -> None:
        self.turn = Symbol.CROSS if self.turn == Symbol.CIRCLE else Symbol.CIRCLE
        if self.winner() == Symbol.CIRCLE:
            self.p1_score += 1
        elif self.winner() == Symbol.CROSS:
            self.p2_score += 1

    def push(self, square: Square, value: Symbol) -> None:
        self.table[square] = value

    def undo(self, square: Square) -> None:
        self.table[square] = Symbol.EMPTY

    def move(self, square: Square) -> None:
        if square >= self.size ** 2 or square < 0 or not self.is_empty(square):
            logger.warning('TIC-TAC-TOE, INVALID MOVE!')
            return

        self.table[square] = self.turn
        self._update()

    def get_player_turn(self) -> Member | int | str:
        return self.player1 if self.turn == Symbol.CIRCLE else self.player2

    def get(self) -> list:
        indexes_with_signs = {}
        for i, square in self.squares.items():
            indexes_with_signs[i] = str(square) if self.is_empty(square) else "O" if self.square_value(
                square) == Symbol.CIRCLE else "X"

        return list(indexes_with_signs.items())
