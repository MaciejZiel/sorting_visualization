from __future__ import annotations

import unittest

from sorting_visualizer.sorting import ALGORITHMS, SortEvent


def apply_event(values: list[int], event: SortEvent) -> None:
    if event.kind == "swap":
        first, second = event.indices
        values[first], values[second] = values[second], values[first]
    elif event.kind == "overwrite":
        values[event.indices[0]] = event.values[0]


class SortingAlgorithmTests(unittest.TestCase):
    def test_algorithms_sort_all_cases(self) -> None:
        cases = [
            [],
            [1],
            [3, 1, 2],
            [5, 4, 3, 2, 1],
            [2, 1, 3, 1],
            [9, 7, 5, 3, 1, 2, 4, 6, 8],
        ]

        for algorithm in ALGORITHMS:
            for case in cases:
                with self.subTest(algorithm=algorithm.key, case=case):
                    values = list(case)
                    for event in algorithm.generator_factory(case):
                        apply_event(values, event)
                    self.assertEqual(values, sorted(case))

    def test_algorithms_emit_in_range_indices(self) -> None:
        source = [7, 3, 5, 1, 9, 2]
        allowed_values = set(source)

        for algorithm in ALGORITHMS:
            with self.subTest(algorithm=algorithm.key):
                for event in algorithm.generator_factory(source):
                    for index in event.indices:
                        self.assertGreaterEqual(index, 0)
                        self.assertLess(index, len(source))
                    for value in event.values:
                        self.assertIn(value, allowed_values)


if __name__ == "__main__":
    unittest.main()
