"""Descriptive combination features for hypothetical sharing risk only."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise


@dataclass(frozen=True)
class SplitRiskFeatures:
    """Observable ticket features; these do not change draw probability."""

    birthday_range_count: int
    above_31_count: int
    consecutive_pairs: int
    arithmetic_sequence: bool
    repeated_last_digit_pairs: int
    all_same_parity: bool
    contains_eight: bool
    contains_four: bool


def split_risk_features(ticket: tuple[int, ...]) -> SplitRiskFeatures:
    """Describe a valid combination without assigning an unsupported HK popularity score."""

    values = tuple(sorted(ticket))
    if len(values) != 6 or len(set(values)) != 6 or values[0] < 1 or values[-1] > 49:
        raise ValueError("ticket must contain six unique numbers from 1 through 49")
    consecutive = sum(right - left == 1 for left, right in pairwise(values))
    differences = {right - left for left, right in pairwise(values)}
    last_digits = [value % 10 for value in values]
    repeated_last = sum(
        last_digits.count(digit) * (last_digits.count(digit) - 1) // 2 for digit in set(last_digits)
    )
    return SplitRiskFeatures(
        birthday_range_count=sum(value <= 31 for value in values),
        above_31_count=sum(value > 31 for value in values),
        consecutive_pairs=consecutive,
        arithmetic_sequence=len(differences) == 1,
        repeated_last_digit_pairs=repeated_last,
        all_same_parity=len({value % 2 for value in values}) == 1,
        contains_eight=8 in values,
        contains_four=4 in values,
    )
