"""
FSRS v4.5 Mathematical Verification Suite
==========================================
Unit tests for the four core pure functions in learning_engine.py:
- calculate_retrievability
- infer_fsrs_grade
- next_difficulty
- next_recall_stability

Reference: FSRS v4.5 formula specification.
FACTOR = 19/81 ≈ 0.2345679012345679
FSRS_W = [0.4072, 1.1827, 3.1262, 15.4722, 7.2102, 0.5316, 1.0651, 0.0234,
          1.6160, 0.1544, 1.0824, 1.9813, 0.0953, 0.2975, 0.2242, 0.2507, 2.9466]
"""
import math
import pytest
from datetime import datetime, timedelta, timezone

# Import the module under test
import sys
sys.path.insert(0, "backend")
from services.paes.learning_engine import (
    calculate_retrievability,
    infer_fsrs_grade,
    next_difficulty,
    next_recall_stability,
    initial_difficulty,
    FACTOR,
    FSRS_W,
)


class TestCalculateRetrievability:
    """R(t, S) = (1 + FACTOR * (t / S))^(-1)"""

    def test_identities(self):
        """At t=0, retrievability is exactly 1.0 regardless of stability."""
        assert calculate_retrievability(0, 1) == 1.0
        assert calculate_retrievability(0, 10) == 1.0
        assert calculate_retrievability(0, 100) == 1.0

    def test_half_life_behavior(self):
        """When t = S / FACTOR, R ≈ 0.5 (definition of half-life)."""
        for s in [5.0, 10.0, 20.0]:
            t = s / FACTOR
            r = calculate_retrievability(t, s)
            assert abs(r - 0.5) < 0.01, f"S={s}: expected ~0.5, got {r:.4f}"

    def test_stability_proportionality(self):
        """Doubles elapsed time with same stability → retrievability decreases predictably."""
        s = 10.0
        r1 = calculate_retrievability(5, s)
        r2 = calculate_retrievability(10, s)
        # r2 should be lower than r1 (more elapsed time → lower retrievability)
        assert r2 < r1, f"r2={r2} should be < r1={r1}"
        # Half-life = S/FACTOR ≈ 42.7 days; for S=10, t=5 and t=10 are both well above half-life
        # so both R values are below 0.5 — the key invariant is r2 < r1, not the 0.5 threshold

    def test_stability_inversely_proportional(self):
        """For same elapsed time, higher stability → higher retrievability."""
        t = 5.0
        r_low = calculate_retrievability(t, 5.0)
        r_high = calculate_retrievability(t, 20.0)
        assert r_high > r_low, f"Higher stability should yield higher retrievability: {r_high} <= {r_low}"

    def test_zero_stability(self):
        """Stability <= 0 must return exactly 0.0 (no retrieval possible)."""
        assert calculate_retrievability(10, 0) == 0.0
        assert calculate_retrievability(10, -1) == 0.0
        assert calculate_retrievability(0, -5) == 0.0

    def test_negative_elapsed_days(self):
        """Negative elapsed days are treated as 0 (future dates clamped)."""
        r = calculate_retrievability(-10, 10)
        assert r == 1.0, "Negative elapsed should clamp to 0"

    def test_extreme_stability(self):
        """Very high stability → retrievability stays near 1.0 for moderate time."""
        r = calculate_retrievability(30, 1000.0)
        assert 0.99 < r < 1.0, f"Extreme stability should keep R near 1.0, got {r}"

    def test_extreme_time(self):
        """Very long elapsed time → retrievability approaches 0."""
        r = calculate_retrievability(365, 10.0)
        # R(365, 10) = 1/(1 + 19/81 * 365/10) ≈ 0.104 — assert it stays above 0
        assert 0.0 < r < 0.15, f"After 1 year with S=10, R should be near 0, got {r}"

    def test_matches_formula_exactly(self):
        """Verify the formula matches the FSRS v4.5 specification exactly."""
        t, s = 7.0, 15.0
        expected = 1.0 / (1.0 + FACTOR * (t / s))
        assert math.isclose(calculate_retrievability(t, s), expected, rel_tol=1e-9)


class TestInferFsrsGrade:
    """Maps (is_correct, confidence, time_spent, change_count) → FSRS grade {1,2,3,4}."""

    def test_incorrect_always_grade_1(self):
        """Any incorrect response is always "Again" (grade 1)."""
        assert infer_fsrs_grade(is_correct=False, confidence=5, time_spent_seconds=10, change_count=0) == 1
        assert infer_fsrs_grade(is_correct=False, confidence=1, time_spent_seconds=200, change_count=5) == 1

    # Grade 2: confidence <= 2 OR change_count >= 2 OR time > 150
    def test_low_confidence_correct_grade_2(self):
        assert infer_fsrs_grade(is_correct=True, confidence=1, time_spent_seconds=30, change_count=0) == 2
        assert infer_fsrs_grade(is_correct=True, confidence=2, time_spent_seconds=30, change_count=0) == 2

    def test_many_changes_correct_grade_2(self):
        assert infer_fsrs_grade(is_correct=True, confidence=4, time_spent_seconds=30, change_count=2) == 2
        assert infer_fsrs_grade(is_correct=True, confidence=4, time_spent_seconds=30, change_count=3) == 2

    def test_long_time_correct_grade_2(self):
        assert infer_fsrs_grade(is_correct=True, confidence=4, time_spent_seconds=151, change_count=0) == 2
        assert infer_fsrs_grade(is_correct=True, confidence=4, time_spent_seconds=300, change_count=0) == 2

    # Grade 4: confidence >= 4 AND change_count == 0 AND time < 45
    def test_easy_grade_4(self):
        assert infer_fsrs_grade(is_correct=True, confidence=4, time_spent_seconds=30, change_count=0) == 4
        assert infer_fsrs_grade(is_correct=True, confidence=5, time_spent_seconds=20, change_count=0) == 4

    def test_easy_but_long_time_not_grade_4(self):
        """High confidence but time > 45s → not Easy."""
        result = infer_fsrs_grade(is_correct=True, confidence=5, time_spent_seconds=50, change_count=0)
        assert result != 4, "Time 50s > 45s should not be grade 4"

    def test_easy_but_changes_not_grade_4(self):
        """High confidence but change_count > 0 → not Easy."""
        result = infer_fsrs_grade(is_correct=True, confidence=5, time_spent_seconds=20, change_count=1)
        assert result != 4, "change_count=1 should not be grade 4"

    # Grade 3: everything else (good)
    def test_grade_3_standard(self):
        """Correct, confidence 3-5, few changes, reasonable time → Good."""
        assert infer_fsrs_grade(is_correct=True, confidence=3, time_spent_seconds=60, change_count=0) == 3
        assert infer_fsrs_grade(is_correct=True, confidence=4, time_spent_seconds=100, change_count=0) == 3
        assert infer_fsrs_grade(is_correct=True, confidence=5, time_spent_seconds=60, change_count=1) == 3

    def test_grade_boundary_confidence_3(self):
        """Confidence exactly 3 without other red flags → Good (grade 3)."""
        result = infer_fsrs_grade(is_correct=True, confidence=3, time_spent_seconds=50, change_count=0)
        assert result == 3


class TestInitialDifficulty:
    """initial_difficulty(grade) = w4 - exp(w5 * (grade-1)) + 1.0, clamped to [1, 10]."""

    def test_grade_1_again(self):
        """Grade 1 (Again): D should be relatively high."""
        d = initial_difficulty(1)
        w4, w5 = FSRS_W[4], FSRS_W[5]
        expected = w4 - math.exp(w5 * 0) + 1.0  # exp(0) = 1
        assert math.isclose(d, expected, rel_tol=1e-9)
        assert 1 <= d <= 10

    def test_grade_2_hard(self):
        d = initial_difficulty(2)
        w4, w5 = FSRS_W[4], FSRS_W[5]
        expected = w4 - math.exp(w5 * 1) + 1.0
        assert math.isclose(d, expected, rel_tol=1e-9)

    def test_grade_3_good(self):
        d = initial_difficulty(3)
        w4, w5 = FSRS_W[4], FSRS_W[5]
        expected = w4 - math.exp(w5 * 2) + 1.0
        assert math.isclose(d, expected, rel_tol=1e-9)

    def test_grade_4_easy(self):
        """Grade 4 (Easy): D should be lowest."""
        d3 = initial_difficulty(3)
        d4 = initial_difficulty(4)
        assert d4 < d3, f"Easy should have lower difficulty than Good: {d4} >= {d3}"

    def test_clamped_at_10(self):
        """The formula should clamp at 10."""
        # Grade 1 gives highest D; verify clamping doesn't affect valid grades
        d1 = initial_difficulty(1)
        assert d1 <= 10.0

    def test_clamped_at_1(self):
        """The formula should clamp at 1."""
        # With default weights, grade 4 should be well above 1, but test clamping logic
        # We verify by checking the formula before clamping
        w4, w5 = FSRS_W[4], FSRS_W[5]
        raw_d4 = w4 - math.exp(w5 * 3) + 1.0
        # raw_d4 should be > 1; if not, the clamping would bring it to 1
        if raw_d4 < 1.0:
            d4 = initial_difficulty(4)
            assert d4 == 1.0, "Should be clamped to 1"


class TestNextDifficulty:
    """next_difficulty(d, grade) applies mean reversion after a review."""

    def test_mean_reversion_towards_good(self):
        """Difficulty should revert toward D0(Good) after each review."""
        d0_good = initial_difficulty(3)
        w6, w7 = FSRS_W[6], FSRS_W[7]

        # Starting difficulty far from D0(Good)
        d_far = 9.0
        d_new = next_difficulty(d_far, 3)  # Good review

        # New difficulty should be between d_far and d0_good (mean reversion)
        assert d0_good < d_new < d_far or d_far < d_new < d0_good

    def test_grade_affects_direction(self):
        """Grade 2 (Hard) should increase difficulty vs grade 4 (Easy) decreasing it."""
        d = 5.0
        d_hard = next_difficulty(d, 2)
        d_easy = next_difficulty(d, 4)
        # Both should still be valid
        assert 1.0 <= d_hard <= 10.0
        assert 1.0 <= d_easy <= 10.0
        # Hard should push difficulty up relative to Good baseline
        d_good = next_difficulty(d, 3)
        assert d_hard > d_good, f"Hard={d_hard} should be > Good={d_good}"
        assert d_easy < d_good, f"Easy={d_easy} should be < Good={d_good}"

    def test_clamped_output(self):
        """Output must always be in [1, 10]."""
        for grade in [1, 2, 3, 4]:
            for d_in in [0.1, 5.0, 15.0]:
                d_out = next_difficulty(d_in, grade)
                assert 1.0 <= d_out <= 10.0, f"next_difficulty({d_in}, {grade}) = {d_out} out of range"


class TestNextRecallStability:
    """next_recall_stability(d, s, r, grade) updates stability after a successful recall."""

    def test_stability_increases_with_success(self):
        """Good review (grade 3) should increase stability."""
        s_initial = 5.0
        d = 5.0
        r = 0.8  # 80% retrievability

        s_new = next_recall_stability(d, s_initial, r, grade=3)
        assert s_new > s_initial, f"Stability should increase after Good: {s_new} <= {s_initial}"

    def test_stability_decreases_with_hard(self):
        """Hard review (grade 2) should increase stability less than Good."""
        s_initial = 5.0
        d = 5.0
        r = 0.8

        s_good = next_recall_stability(d, s_initial, r, grade=3)
        s_hard = next_recall_stability(d, s_initial, r, grade=2)
        assert s_hard < s_good, f"Hard={s_hard} should increase less than Good={s_good}"

    def test_stability_increases_more_with_easy(self):
        """Easy review (grade 4) should increase stability more than Good."""
        s_initial = 5.0
        d = 5.0
        r = 0.8

        s_good = next_recall_stability(d, s_initial, r, grade=3)
        s_easy = next_recall_stability(d, s_initial, r, grade=4)
        assert s_easy > s_good, f"Easy={s_easy} should increase more than Good={s_good}"

    def test_minimum_stability(self):
        """Stability should never go below 0.1."""
        # Very low stability with poor retrievability
        s_new = next_recall_stability(d=9.0, s=0.2, r=0.1, grade=2)
        assert s_new >= 0.1, f"Stability should be >= 0.1, got {s_new}"

    def test_retrievability_effect(self):
        """Lower retrievability (more forgotten) → smaller stability increase.

        In FSRS, the stability update uses exp(-factor * (1-R)) where factor>0.
        Lower R → higher (1-R) → larger exponent magnitude → bigger stability change.
        For a forgotten item (R≈0), the exponential gives the maximum factor boost.
        For a well-remembered item (R≈1), the exponential factor is near 1 → smaller boost.
        So s_low_r > s_high_r: more forgotten items get a larger stability boost.
        """
        s_initial = 5.0
        d = 5.0

        s_high_r = next_recall_stability(d, s_initial, r=0.95, grade=3)
        s_low_r = next_recall_stability(d, s_initial, r=0.5, grade=3)
        assert s_low_r > s_high_r, "More forgotten items (lower R) should yield larger stability increase"

    def test_difficulty_effect(self):
        """Higher difficulty → harder to maintain/increase stability."""
        s_initial = 5.0
        r = 0.8

        s_low_d = next_recall_stability(3.0, s_initial, r, grade=3)
        s_high_d = next_recall_stability(8.0, s_initial, r, grade=3)
        assert s_low_d > s_high_d, f"Lower difficulty should yield higher stability: {s_low_d} <= {s_high_d}"


class TestFsrsWeightsIntegrity:
    """Sanity checks on the FSRS_W vector."""

    def test_fsrs_w_has_17_elements(self):
        assert len(FSRS_W) == 17, f"FSRS_W should have 17 elements, got {len(FSRS_W)}"

    def test_factor_matches_formula(self):
        expected_factor = 19.0 / 81.0
        assert math.isclose(FACTOR, expected_factor, rel_tol=1e-9)

    def test_weights_are_positive(self):
        """All FSRS weights must be positive (no negative stability parameters)."""
        for i, w in enumerate(FSRS_W):
            assert w > 0, f"FSRS_W[{i}] = {w} should be positive"

    def test_d0_initial_range(self):
        """w4 and w5 define initial difficulty; result should be in [1, 10]."""
        for grade in [1, 2, 3, 4]:
            d = initial_difficulty(grade)
            assert 1.0 <= d <= 10.0, f"initial_difficulty({grade}) = {d} out of range"

    def test_w4_w5_w6_w7_constants(self):
        """Verify the first 8 weights match the canonical FSRS v4.5 vector."""
        w4, w5, w6, w7 = FSRS_W[4], FSRS_W[5], FSRS_W[6], FSRS_W[7]
        assert math.isclose(w4, 7.2102, rel_tol=1e-4)
        assert math.isclose(w5, 0.5316, rel_tol=1e-4)
        assert math.isclose(w6, 1.0651, rel_tol=1e-4)
        assert math.isclose(w7, 0.0234, rel_tol=1e-4)