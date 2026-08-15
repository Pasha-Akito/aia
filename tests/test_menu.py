from __future__ import annotations

import unittest

from aia.menu import select_paged


class MenuTests(unittest.TestCase):
    def run_menu(self, values: list[str], choices: list[str]):
        output: list[str] = []
        entered = iter(choices)
        selected = select_paged(
            "Choose:", values, str, input_fn=lambda _: next(entered), output=output.append
        )
        return selected, output

    def test_zero_exits(self) -> None:
        selected, output = self.run_menu(["one"], ["0"])
        self.assertIsNone(selected)
        self.assertEqual(output[0], "Choose:")

    def test_next_and_previous_pages(self) -> None:
        selected, output = self.run_menu([str(index) for index in range(10)], ["9", "8", "1"])
        self.assertEqual(selected, "0")
        self.assertEqual(output.count("Choose:"), 3)

    def test_unavailable_pages_do_nothing(self) -> None:
        selected, output = self.run_menu(["one"], ["8", "9", "1"])
        self.assertEqual(selected, "one")
        self.assertEqual(output.count("Choose:"), 3)

    def test_invalid_input_reprompts(self) -> None:
        selected, _ = self.run_menu(["one"], ["hello", "7", "1"])
        self.assertEqual(selected, "one")

    def test_eof_exits(self) -> None:
        selected = select_paged(
            "Choose:",
            ["one"],
            str,
            input_fn=lambda _: (_ for _ in ()).throw(EOFError()),
            output=lambda _: None,
        )
        self.assertIsNone(selected)


if __name__ == "__main__":
    unittest.main()
