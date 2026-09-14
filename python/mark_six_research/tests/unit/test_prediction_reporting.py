from mark_six.prediction.reporting import replication_models_to_report


def test_replication_report_keeps_best_alternative_when_uniform_is_better() -> None:
    rows: list[dict[str, object]] = [
        {"period_id": "pool45", "model": "uniform", "mean_log_score_difference_nats": 0.0},
        {"period_id": "pool45", "model": "frequency", "mean_log_score_difference_nats": -0.1},
        {"period_id": "pool45", "model": "recent", "mean_log_score_difference_nats": -0.02},
        {"period_id": "pool47", "model": "uniform", "mean_log_score_difference_nats": 0.0},
        {"period_id": "pool47", "model": "frequency", "mean_log_score_difference_nats": -0.03},
    ]

    selected = replication_models_to_report(rows)

    assert selected == {
        ("pool45", "uniform"),
        ("pool45", "recent"),
        ("pool47", "uniform"),
        ("pool47", "frequency"),
    }
