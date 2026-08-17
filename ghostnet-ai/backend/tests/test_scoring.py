import os
import sys
import enum
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.scoring import calculate_priority_score_pure, CATEGORY_WEIGHTS


class MockSosCategoryEnum(str, enum.Enum):
    MEDICAL = "medical"
    DISASTER = "disaster"
    SECURITY = "security"
    GENERAL = "general"


def test_worked_example_priority_score():
    now = datetime.now(timezone.utc)
    created_at = now - timedelta(minutes=5)

    # Medical alert, 5 mins old, 2 corroborations, 0.8 dead zone score
    score, breakdown = calculate_priority_score_pure(
        category=MockSosCategoryEnum.MEDICAL,
        created_at=created_at,
        corroboration_count=2,
        location_risk=0.8,
        now=now,
    )

    print(f"Calculated Score: {score}")
    print(f"Breakdown: {breakdown}")

    assert 0.81 <= score <= 0.83, f"Score {score} out of expected ~0.82 range"
    assert breakdown["category_term"] == 0.40
    assert breakdown["corroboration_term"] == 0.08
    assert breakdown["location_risk_term"] == 0.12
    print("Priority scoring engine test passed successfully!")


if __name__ == "__main__":
    test_worked_example_priority_score()

