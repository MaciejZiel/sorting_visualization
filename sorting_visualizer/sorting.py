from __future__ import annotations

from collections.abc import Callable, Generator
from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class SortEvent:
    kind: str
    indices: tuple[int, ...] = ()
    values: tuple[int, ...] = ()


SortGenerator = Generator[SortEvent, None, None]


@dataclass(slots=True, frozen=True)
class AlgorithmDefinition:
    key: str
    label: str
    description: str
    generator_factory: Callable[[list[int]], SortGenerator]


def compare(*indices: int) -> SortEvent:
    return SortEvent("compare", tuple(indices))


def swap(i: int, j: int) -> SortEvent:
    return SortEvent("swap", (i, j))


def overwrite(index: int, value: int) -> SortEvent:
    return SortEvent("overwrite", (index,), (value,))


def mark_sorted(*indices: int) -> SortEvent:
    return SortEvent("mark_sorted", tuple(indices))


def bubble_sort(values: list[int]) -> SortGenerator:
    items = list(values)
    length = len(items)

    if length <= 1:
        if length == 1:
            yield mark_sorted(0)
        return

    for end in range(length - 1, 0, -1):
        swapped_any = False
        for index in range(end):
            yield compare(index, index + 1)
            if items[index] > items[index + 1]:
                items[index], items[index + 1] = items[index + 1], items[index]
                swapped_any = True
                yield swap(index, index + 1)
        yield mark_sorted(end)
        if not swapped_any:
            return


def selection_sort(values: list[int]) -> SortGenerator:
    items = list(values)
    length = len(items)

    if length <= 1:
        if length == 1:
            yield mark_sorted(0)
        return

    for start in range(length - 1):
        min_index = start
        for index in range(start + 1, length):
            yield compare(min_index, index)
            if items[index] < items[min_index]:
                min_index = index
        if min_index != start:
            items[start], items[min_index] = items[min_index], items[start]
            yield swap(start, min_index)
        yield mark_sorted(start)


def insertion_sort(values: list[int]) -> SortGenerator:
    items = list(values)

    if len(items) <= 1:
        if items:
            yield mark_sorted(0)
        return

    for index in range(1, len(items)):
        cursor = index
        while cursor > 0:
            yield compare(cursor - 1, cursor)
            if items[cursor - 1] <= items[cursor]:
                break
            items[cursor - 1], items[cursor] = items[cursor], items[cursor - 1]
            yield swap(cursor - 1, cursor)
            cursor -= 1


def merge_sort(values: list[int]) -> SortGenerator:
    items = list(values)

    if len(items) <= 1:
        if items:
            yield mark_sorted(0)
        return

    def _merge_sort(left: int, right: int) -> SortGenerator:
        if left >= right:
            return
        middle = (left + right) // 2
        yield from _merge_sort(left, middle)
        yield from _merge_sort(middle + 1, right)
        yield from _merge(left, middle, right)

    def _merge(left: int, middle: int, right: int) -> SortGenerator:
        left_slice = items[left : middle + 1]
        right_slice = items[middle + 1 : right + 1]
        left_index = 0
        right_index = 0
        write_index = left

        while left_index < len(left_slice) and right_index < len(right_slice):
            yield compare(left + left_index, middle + 1 + right_index)
            if left_slice[left_index] <= right_slice[right_index]:
                items[write_index] = left_slice[left_index]
                yield overwrite(write_index, left_slice[left_index])
                left_index += 1
            else:
                items[write_index] = right_slice[right_index]
                yield overwrite(write_index, right_slice[right_index])
                right_index += 1
            write_index += 1

        while left_index < len(left_slice):
            items[write_index] = left_slice[left_index]
            yield overwrite(write_index, left_slice[left_index])
            left_index += 1
            write_index += 1

        while right_index < len(right_slice):
            items[write_index] = right_slice[right_index]
            yield overwrite(write_index, right_slice[right_index])
            right_index += 1
            write_index += 1

    yield from _merge_sort(0, len(items) - 1)


def quick_sort(values: list[int]) -> SortGenerator:
    items = list(values)

    if len(items) <= 1:
        if items:
            yield mark_sorted(0)
        return

    def _quick_sort(low: int, high: int) -> SortGenerator:
        if low > high:
            return
        if low == high:
            yield mark_sorted(low)
            return

        pivot = items[high]
        store_index = low - 1

        for index in range(low, high):
            yield compare(index, high)
            if items[index] <= pivot:
                store_index += 1
                if store_index != index:
                    items[store_index], items[index] = items[index], items[store_index]
                    yield swap(store_index, index)

        pivot_index = store_index + 1
        if pivot_index != high:
            items[pivot_index], items[high] = items[high], items[pivot_index]
            yield swap(pivot_index, high)

        yield mark_sorted(pivot_index)
        yield from _quick_sort(low, pivot_index - 1)
        yield from _quick_sort(pivot_index + 1, high)

    yield from _quick_sort(0, len(items) - 1)


ALGORITHMS = [
    AlgorithmDefinition("bubble", "Bubble Sort", "Classic pairwise swapping with a clear bubbling pass.", bubble_sort),
    AlgorithmDefinition("selection", "Selection Sort", "Repeatedly selects the minimum and places it in front.", selection_sort),
    AlgorithmDefinition("insertion", "Insertion Sort", "Builds a sorted prefix by sliding values into place.", insertion_sort),
    AlgorithmDefinition("merge", "Merge Sort", "Divide-and-conquer with overwrite-based merging steps.", merge_sort),
    AlgorithmDefinition("quick", "Quick Sort", "Pivot partitioning with fast large-scale movement.", quick_sort),
]

ALGORITHM_BY_KEY = {algorithm.key: algorithm for algorithm in ALGORITHMS}
