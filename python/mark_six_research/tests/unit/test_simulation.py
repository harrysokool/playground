from random import Random

from mark_six.mathematics.evidence import EvidenceType
from mark_six.mathematics.simulation import (
    generate_fair_draw,
    generate_valid_ticket,
    simulate_ticket_outcomes,
)


def test_ticket_and_draw_generation_are_valid_for_supported_pools() -> None:
    for pool_size in (45, 47, 49):
        random_source = Random(123)
        ticket = generate_valid_ticket(pool_size, random_source)
        main, extra = generate_fair_draw(pool_size, random_source)

        assert len(ticket) == len(set(ticket)) == 6
        assert all(1 <= number <= pool_size for number in ticket)
        assert len(main) == 6
        assert extra not in main
        assert all(1 <= number <= pool_size for number in (*main, extra))


def test_simulation_is_reproducible() -> None:
    first = simulate_ticket_outcomes(
        pool_size=49,
        prize_divisions=7,
        trials=2_000,
        seed=999,
        ticket=(1, 2, 3, 4, 5, 6),
    )
    second = simulate_ticket_outcomes(
        pool_size=49,
        prize_divisions=7,
        trials=2_000,
        seed=999,
        ticket=(1, 2, 3, 4, 5, 6),
    )

    assert first == second


def test_simulation_converges_with_justified_tolerance() -> None:
    result = simulate_ticket_outcomes(
        pool_size=49,
        prize_divisions=7,
        trials=100_000,
        seed=20260913,
        ticket=(1, 2, 3, 4, 5, 6),
    )

    assert result.evidence_type == EvidenceType.SIMULATION_ESTIMATE
    assert all(comparison.within_tolerance for comparison in result.comparisons)
    estimated_any = sum(
        comparison.estimated_probability
        for comparison in result.comparisons
        if comparison.outcome != "no_prize"
    )
    exact_any = sum(
        comparison.exact_probability
        for comparison in result.comparisons
        if comparison.outcome != "no_prize"
    )
    assert abs(float(estimated_any - exact_any)) < 0.002
