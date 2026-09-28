"""Детерминированный выбор фраз из пулов вариантов.

Требования к выбору варианта:
  * детерминированность - одни и те же входные данные всегда дают
    одинаковое письмо (иначе тесты будут нестабильны);
  * разнообразие - блоки одного письма не повторяют одну и ту же фразу,
    а разные входные данные дают разные формулировки.
"""

from __future__ import annotations

import hashlib
from typing import Sequence, TypeVar

T = TypeVar("T")


class PhrasePicker:
    """Выбирает варианты фраз на основе хеша входных данных."""

    def __init__(self, seed: str) -> None:
        self.seed = seed or ""
        self._used: set = set()

    def _digest(self, slot: str, size: int) -> int:
        payload = f"{self.seed}|{slot}|{size}".encode("utf-8")
        return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")

    def pick(self, pool: Sequence[T], slot: str) -> T:
        """Возвращает один вариант из пула.

        Если вариант уже использован в этом письме, выбирается следующий -
        так письмо не начинает звучать одинаково.
        """
        if not pool:
            raise ValueError("Пул фраз не может быть пустым")
        if len(pool) == 1:
            return pool[0]

        start = self._digest(slot, len(pool)) % len(pool)
        for offset in range(len(pool)):
            candidate = pool[(start + offset) % len(pool)]
            key = (slot, candidate if isinstance(candidate, str) else repr(candidate))
            if key not in self._used:
                self._used.add(key)
                return candidate
        # Все варианты заняты (бывает только при крошечных пулах) - берём первый свободный слот.
        chosen = pool[start]
        self._used.add((slot, chosen if isinstance(chosen, str) else repr(chosen)))
        return chosen

    def pick_many(self, pool: Sequence[T], slot: str, count: int) -> list:
        """Возвращает до `count` разных вариантов из пула."""
        return [self.pick(pool, f"{slot}#{index}") for index in range(max(0, count))]
