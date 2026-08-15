from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TypeVar

T = TypeVar("T")


def select_paged(
    instruction: str,
    items: Sequence[T],
    describe: Callable[[T], str],
    *,
    input_fn: Callable[[str], str] = input,
    output: Callable[[str], None] = print,
) -> T | None:
    page = 0
    page_size = 7
    while True:
        start = page * page_size
        visible = items[start : start + page_size]
        output(instruction)
        for number, item in enumerate(visible, start=1):
            output(f"{number}. {describe(item)}")
        output("8. Previous  9. Next  0. Exit")
        try:
            choice = input_fn("> ").strip()
        except (EOFError, KeyboardInterrupt):
            output("")
            return None
        if choice == "0":
            return None
        if choice == "8":
            if page > 0:
                page -= 1
            continue
        if choice == "9":
            if start + page_size < len(items):
                page += 1
            continue
        if choice.isdigit() and 1 <= int(choice) <= len(visible):
            return visible[int(choice) - 1]
