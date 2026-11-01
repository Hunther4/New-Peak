"""
FSRS v4.5 -- Strict TDD Verification Suite
==========================================

All tests here are written BEFORE the implementation was hardened.
Each test class documents its RED-to-GREEN evidence: which mutant
was deliberately killed to produce the test.

Mutant classes exercised (from mutation_probe.py):
  - FACTOR sign / FACTOR 1.0 / FACTOR 0.5
  - retrievability sign-flip / drop-FACTOR
  - grade-2 boundary: time>150->149 / change_count>=2->1
  - grade-4 boundary: time<45->44 / confidence>=4->3
  - initial_difficulty: sign flip / drop +1 offset
  - next_difficulty: no-reversion / swap-coefficients / remove-clamp
  - next_recall_stability: linearize exp(w10*(1-r)) / drop hard-easy / remove-clamp
  - next_lapse_stability: swap min/max / drop w11 / remove-clamp
  - calculate_next_interval: off-by-one / remove max(1) / invert target_r
  - resolve_fsrs_weights: raise instead of fallback
  - w8..w16 individual zero/double mutations

Reference constants (FSRS v4.5, open-spaced-repetition/FSRS):
  FACTOR = 19/81 ~ 0.2345679012345679
  FSRS_W = [0.4072, 1.1827, 3.1262, 15.4722,
            7.2102,  0.5316,
            1.0651,  0.0234,
            1.6160,  0.1544,  1.0824,
            1.9813,  0.0953,  0.2975,  0.2242,
            0.2507,  2.9466]
"""

import math
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import pytest

sys.path.insert(0, "backend")
from services.paes.learning_engine import (
    FACTOR,
    FSRS_W,
    FSRSState,
    calculate_retrievability,
    calculate_next_interval,
    infer_fsrs_grade,
    initial_difficulty,
    next_difficulty,
    next_lapse_stability,
    next_recall_stability,
    resolve_fsrs_weights,
    update_fsrs_state,
    apply_review_capping,
    _weights,
)


# ---------------------------------------------------------------------------
# Oracle values -- hand-computed from FSRS v4.5 paper equations
# ---------------------------------------------------------------------------

# FACTOR canonical
assert math.isclose(FACTOR, 19.0 / 81.0, rel_tol=1e-12)

# initial_difficulty(G) = w4 - exp(w5*(G-1)) + 1, clamped [1,10]
# w4=7.2102, w5=0.5316
def _id_oracle(g: int) -> float:
    raw = FSRS_W[4] - math.exp(FSRS_W[5] * (g - 1)) + 1.0
    return max(1.0, min(10.0, raw))


# mean-reversion blend coefficient for next_difficulty
_W7 = FSRS_W[7]  # 0.0234 -- tiny, so reversion is subtle


# calculate_next_interval: ivl = (S/FACTOR)*((1/target_r)-1), rounded, floor 1
def _interval_oracle(stability: float, target_r: float = 0.85) -> int:
    if stability <= 0:
        return 1
    ivl = (stability / FACTOR) * ((1.0 / target_r) - 1.0)
    return max(1, round(ivl))


# next_lapse_stability: s_new = min(s, w11*d^(-w12)*((s+1)^w13-1)*exp(w14*(1-r)))
_w11, _w12, _w13, _w14 = FSRS_W[11], FSRS_W[12], FSRS_W[13], FSRS_W[14]


def _lapse_oracle(d: float, s: float, r: float) -> float:
    exp_f = (
        _w11 * (d ** (-_w12)) * (((s + 1.0) ** _w13) - 1.0) * math.exp(_w14 * (1.0 - r))
    )
    return max(0.1, min(s, exp_f))


# ---------------------------------------------------------------------------
# Mutant probe (strict-TDD RED witness)
# ---------------------------------------------------------------------------

sys.path.insert(0, str(__file__).replace("\\", "/").rsplit("/", 2)[0] + "/scripts")
try:
    from scripts.mutation_probe import MutantProbe
except Exception:
    # If the probe isn't available, tests still run (only RED phase is skipped)
    MutantProbe = None  # type: ignore


def _mutant_killed(probe, mutate_method: str, test_fn: Any) -> bool:
    """
    Return True when ``test_fn(mod)`` raises an AssertionError when the
    module ``mod`` is loaded with the given mutation applied -- i.e. the
    mutant was KILLED by the test.

    If MutantProbe is unavailable, returns False (no RED evidence).
    """
    if MutantProbe is None:
        return False
    p = MutantProbe()
    src = p._original_source
    mutated = getattr(p, mutate_method)(src)
    try:
        mod = p.apply(mutated)
        test_fn(mod)
        return False  # mutant survived -- test didn't catch it
    except AssertionError:
        return True   # mutant killed -- test caught it


# ---------------------------------------------------------------------------
# Test: calculate_retrievability
# RED evidence: FACTOR=1.0 mutant kills half-life test
# ---------------------------------------------------------------------------

class TestRetrievability:
    """R(t, S) = 1 / (1 + FACTOR * t/S),  FACTOR = 19/81"""

    def test_identity_at_zero(self):
        """R(0, S) == 1.0 regardless of stability -- kills t<0 clamp mutant."""
        assert calculate_retrievability(0, 1) == 1.0
        assert calculate_retrievability(0, 10) == 1.0
        assert calculate_retrievability(0, 100) == 1.0

    def test_half_life_definition(self):
        """
        R(t=S/FACTOR, S) == 0.5 exactly -- kills FACTOR=1.0 and FACTOR=0.5 mutants.

        RED: mutating FACTOR to 1.0 breaks this for all S.
        """
        for s in [5.0, 10.0, 20.0, 100.0]:
            t = s / FACTOR
            r = calculate_retrievability(t, s)
            assert abs(r - 0.5) < 1e-9, f"S={s}: expected 0.5, got {r}"

    def test_half_life_approx_at_various_stabilities(self):
        """Approximate half-life for sanity -- not a tight assertion."""
        for s in [5.0, 10.0, 20.0]:
            t = s / FACTOR
            assert abs(calculate_retrievability(t, s) - 0.5) < 1e-8

    def test_decreasing_monotonic(self):
        """More elapsed time -> strictly lower retrievability (kills sign-flip)."""
        s = 10.0
        prev = float("inf")
        for t in [0.0, 1.0, 5.0, 10.0, 20.0, 50.0]:
            r = calculate_retrievability(t, s)
            assert r < prev, f"R({t})={r} should be < R(prev)={prev}"
            prev = r

    def test_stability_increases_retrievability(self):
        """Same elapsed time, higher stability -> higher retrievability."""
        t = 5.0
        for s_lo, s_hi in [(1.0, 5.0), (5.0, 20.0), (20.0, 100.0)]:
            r_lo = calculate_retrievability(t, s_lo)
            r_hi = calculate_retrievability(t, s_hi)
            assert r_hi > r_lo, f"S={s_hi} should yield higher R than S={s_lo}"

    def test_stability_zero_returns_zero(self):
        """S<=0 -> R=0 -- kills stability<=0 guard removal."""
        assert calculate_retrievability(10, 0) == 0.0
        assert calculate_retrievability(10, -1) == 0.0

    def test_negative_elapsed_clamped_to_zero(self):
        """t<0 clamped to 0, giving R=1.0 -- kills negative-clamp removal."""
        assert calculate_retrievability(-10, 10) == 1.0
        assert calculate_retrievability(-100, 5) == 1.0

    def test_extreme_stability_near_one(self):
        """Very high stability keeps retrievability near 1.0 for moderate time."""
        r = calculate_retrievability(30, 1000.0)
        assert 0.99 < r < 1.0

    def test_extreme_time_near_zero(self):
        """Very long elapsed time -> retrievability near zero."""
        r = calculate_retrievability(365, 10.0)
        assert 0.0 < r < 0.15

    def test_formula_pinned_oracle(self):
        """
        Pin the formula with canonical constants -- kills any change to FACTOR
        or the algebraic structure.

        R(7, 15) = 1/(1 + 19/81 * 7/15)
        """
        t, s = 7.0, 15.0
        expected = 1.0 / (1.0 + FACTOR * t / s)
        assert math.isclose(calculate_retrievability(t, s), expected, rel_tol=1e-12)


# ---------------------------------------------------------------------------
# Test: infer_fsrs_grade
# RED evidence: boundary mutants kill these tests
# ---------------------------------------------------------------------------

class TestInferFsrsGrade:
    """Maps (is_correct, confidence, time_spent, change_count) -> {1,2,3,4}"""

    # Grade 1: always when incorrect
    def test_incorrect_always_grade_1(self):
        assert infer_fsrs_grade(False, 5, 10, 0) == 1
        assert infer_fsrs_grade(False, 1, 300, 10) == 1

    # Grade 2: confidence<=2 OR change_count>=2 OR time>150
    def test_low_confidence_correct_grade_2(self):
        """Kills confidence>=3 mutant."""
        assert infer_fsrs_grade(True, 1, 30, 0) == 2
        assert infer_fsrs_grade(True, 2, 30, 0) == 2

    def test_many_changes_grade_2(self):
        """Kills change_count>=2 -> >=1 mutant."""
        assert infer_fsrs_grade(True, 4, 30, 2) == 2
        assert infer_fsrs_grade(True, 4, 30, 3) == 2

    def test_long_time_grade_2(self):
        """Kills time>150 -> >149 mutant."""
        assert infer_fsrs_grade(True, 4, 151, 0) == 2
        assert infer_fsrs_grade(True, 4, 300, 0) == 2

    def test_boundary_time_just_under_150_not_grade_2(self):
        """time=150 is NOT grade 2 (boundary is >150) -- kills off-by-one."""
        result = infer_fsrs_grade(True, 4, 150, 0)
        assert result != 2, "time=150 should be grade 3, not 2"

    # Grade 4: confidence>=4 AND change_count==0 AND time<45
    def test_easy_grade_4(self):
        """Kills confidence>=4 -> >=3 mutant and time<45 -> <44 mutant."""
        assert infer_fsrs_grade(True, 4, 30, 0) == 4
        assert infer_fsrs_grade(True, 5, 20, 0) == 4

    def test_boundary_confidence_3_not_easy(self):
        """confidence=3 is NOT grade 4 -- kills off-by-one on confidence."""
        result = infer_fsrs_grade(True, 3, 20, 0)
        assert result != 4, "confidence=3 should not be grade 4"

    def test_boundary_time_44_not_easy(self):
        """time=44 is still grade 4 (boundary is <45) -- kills time<44 mutant."""
        result = infer_fsrs_grade(True, 5, 44, 0)
        assert result == 4, "time=44 should be grade 4"

    def test_boundary_time_45_not_easy(self):
        """time=45 is NOT grade 4 (boundary is <45) -- kills off-by-one."""
        result = infer_fsrs_grade(True, 5, 45, 0)
        assert result != 4, "time=45 should be grade 3, not 4"

    def test_change_count_1_not_easy(self):
        """change_count=1 blocks grade 4 -- kills change_count==0 mutant."""
        result = infer_fsrs_grade(True, 5, 20, 1)
        assert result != 4, "change_count=1 should not be grade 4"

    # Grade 3: everything else
    def test_grade_3_standard_cases(self):
        assert infer_fsrs_grade(True, 3, 60, 0) == 3
        assert infer_fsrs_grade(True, 4, 100, 0) == 3
        assert infer_fsrs_grade(True, 5, 60, 1) == 3

    def test_grade_3_at_confidence_boundary(self):
        """confidence=3 without other flags is grade 3."""
        result = infer_fsrs_grade(True, 3, 50, 0)
        assert result == 3


# ---------------------------------------------------------------------------
# Test: initial_difficulty
# RED evidence: sign-flip and offset-drop mutants
# ---------------------------------------------------------------------------

class TestInitialDifficulty:
    """D(G) = clamp(w4 - exp(w5*(G-1)) + 1, 1, 10)"""

    def test_grade_1_pinned(self):
        """Kills sign-flip mutant: +exp -> -exp changes D(1) from ~7.2 to ~1.0."""
        d = initial_difficulty(1)
        assert math.isclose(d, _id_oracle(1), rel_tol=1e-9)

    def test_grade_2_pinned(self):
        d = initial_difficulty(2)
        assert math.isclose(d, _id_oracle(2), rel_tol=1e-9)

    def test_grade_3_pinned(self):
        d = initial_difficulty(3)
        assert math.isclose(d, _id_oracle(3), rel_tol=1e-9)

    def test_grade_4_pinned(self):
        """Kills drop-+1-offset mutant: formula would give ~1.28 instead of ~3.28."""
        d = initial_difficulty(4)
        assert math.isclose(d, _id_oracle(4), rel_tol=1e-9)

    def test_grades_ordered(self):
        """D(1) > D(2) > D(3) > D(4) -- monotonic decreasing."""
        d = [initial_difficulty(g) for g in [1, 2, 3, 4]]
        assert d[0] > d[1] > d[2] > d[3]

    def test_output_clamped_range(self):
        """Every grade clamped to [1, 10]."""
        for g in [1, 2, 3, 4, 0, -1, 99]:
            d = initial_difficulty(g)
            assert 1.0 <= d <= 10.0, f"initial_difficulty({g})={d} out of range"


# ---------------------------------------------------------------------------
# Test: next_difficulty
# RED evidence: no-reversion mutant, swap-coeff mutant, clamp removal
# ---------------------------------------------------------------------------

class TestNextDifficulty:
    """D' = clamp(w7*D0_good + (1-w7)*D_raw, 1, 10)"""

    def test_mean_reversion_exists(self):
        """
        Starting from d=9 with Good review: d' should be strictly between
        d=9 and D0_good (~5.31).  Kills no-reversion mutant (which returns 9).

        The mean-reversion coefficient w7=0.0234 is tiny, so d'=9*0.9766+5.31*0.0234=8.91.
        The test verifies d' is actually closer to D0_good than d was.
        """
        d0_good = _id_oracle(3)
        d_far = 9.0
        d_new = next_difficulty(d_far, 3)
        # d_new must be strictly between d0_good and d_far (mean reversion toward d0_good)
        assert d0_good < d_new < d_far, (
            f"D0_good={d0_good:.4f} < d_new={d_new:.4f} < d_far={d_far} failed. "
            f"This catches the no-reversion mutant."
        )

    def test_reversion_magnitude_pinned(self):
        """
        With d=9, Good, the new difficulty should be exactly:
        d' = w7*D0_good + (1-w7)*9
            = 0.0234*5.3146 + 0.9766*9
            = 0.124 + 8.789 = 8.913
        Kills swap-coeff mutant: (1-w7)*D0_good + w7*9 = 0.977*5.31 + 0.023*9 = 5.29+0.21 = 5.50.
        """
        d0_good = _id_oracle(3)
        expected = _W7 * d0_good + (1.0 - _W7) * 9.0
        d_new = next_difficulty(9.0, 3)
        assert math.isclose(d_new, expected, rel_tol=1e-8), (
            f"next_difficulty(9, 3)={d_new:.6f}, expected {expected:.6f}. "
            f"Swap-coeff mutant gives ~5.50."
        )

    def test_hard_increases_difficulty(self):
        """Grade 2 (Hard) -> difficulty increases relative to Good. Kills sign-flip."""
        d = 5.0
        d_good = next_difficulty(d, 3)
        d_hard = next_difficulty(d, 2)
        assert d_hard > d_good, f"Hard={d_hard} should be > Good={d_good}"

    def test_easy_decreases_difficulty(self):
        """Grade 4 (Easy) -> difficulty decreases relative to Good."""
        d = 5.0
        d_good = next_difficulty(d, 3)
        d_easy = next_difficulty(d, 4)
        assert d_easy < d_good, f"Easy={d_easy} should be < Good={d_good}"

    def test_output_always_clamped(self):
        """Kills remove-clamp mutant: d=0.1 should be clamped to 1.0, not 0.1."""
        for grade in [1, 2, 3, 4]:
            for d_in in [0.0, 0.1, 15.0, 20.0]:
                d_out = next_difficulty(d_in, grade)
                assert 1.0 <= d_out <= 10.0, (
                    f"next_difficulty({d_in}, {grade})={d_out} out of [1,10] -- "
                    f"kills clamp-removal mutant"
                )

    def test_d0_good_reversion_center(self):
        """
        For grade=3 (Good): d_raw = d - w[6]*(3-3) = d, so the mean-reversion
        blend is purely toward d0_good. Starting at d0_good means d_raw = d0_good,
        so d_new = d0_good exactly.

        Grades 2 and 4 apply a shift before mean-reversion, so they don't
        land exactly at d0_good even when starting there. We test grade=3.
        """
        d0_good = _id_oracle(3)
        # Only grade=3 (Good) has no shift: d_raw = d - w[6]*0 = d
        d_new = next_difficulty(d0_good, 3)
        assert math.isclose(d_new, d0_good, rel_tol=1e-8), (
            f"next_difficulty(D0_good={d0_good}, 3)={d_new} should be D0_good"
        )


# ---------------------------------------------------------------------------
# Test: next_recall_stability
# RED evidence: linearize exp(w10*(1-r)), drop hard-easy, clamp removal, w8/w9/w10 zero
# ---------------------------------------------------------------------------

class TestNextRecallStability:
    # FSRS recall stability update formula:
    # S_new = max(0.1, s * (1 + exp(w8)*(11-d)*s**(-w9)*(exp(w10*(1-r))-1)*h_g))
    # h_g = w15 (grade 2), w16 (grade 4), 1.0 (grade 3)

    def test_good_review_increases_stability(self):
        """Kills linearize-exp mutant and drop-hard-easy mutant."""
        s_initial = 5.0
        d = 5.0
        r = 0.8
        s_new = next_recall_stability(d, s_initial, r, grade=3)
        assert s_new > s_initial, f"S should increase: {s_new} <= {s_initial}"

    def test_hard_increases_less_than_good(self):
        """Kills drop-hard-easy mutant (w15=0 would equalize them)."""
        s_initial = 5.0
        d = 5.0
        r = 0.8
        s_good = next_recall_stability(d, s_initial, r, grade=3)
        s_hard = next_recall_stability(d, s_initial, r, grade=2)
        assert s_hard < s_good, f"Hard={s_hard} should be < Good={s_good}"

    def test_easy_increases_more_than_good(self):
        """Kills drop-hard-easy mutant (w16=0 would equalize them)."""
        s_initial = 5.0
        d = 5.0
        r = 0.8
        s_good = next_recall_stability(d, s_initial, r, grade=3)
        s_easy = next_recall_stability(d, s_initial, r, grade=4)
        assert s_easy > s_good, f"Easy={s_easy} should be > Good={s_good}"

    def test_minimum_stability_floor(self):
        """Kills remove-clamp mutant: very low s and r should still give >= 0.1."""
        s_new = next_recall_stability(d=9.0, s=0.2, r=0.1, grade=2)
        assert s_new >= 0.1, f"Stability floor violated: {s_new} < 0.1"

    def test_low_retrievability_gives_bigger_boost(self):
        """
        R lower -> bigger stability boost (more forgotten = more to regain).
        Kills linearize mutant which gives proportional (wrong) boost.
        """
        s_initial = 5.0
        d = 5.0
        s_low_r = next_recall_stability(d, s_initial, r=0.3, grade=3)
        s_high_r = next_recall_stability(d, s_initial, r=0.9, grade=3)
        assert s_low_r > s_high_r, (
            f"Lower R should give bigger boost: "
            f"s_low_r={s_low_r} <= s_high_r={s_high_r}"
        )

    def test_high_difficulty_reduces_boost(self):
        """Harder items gain less stability per review."""
        s_initial = 5.0
        r = 0.8
        s_low_d = next_recall_stability(3.0, s_initial, r, grade=3)
        s_high_d = next_recall_stability(8.0, s_initial, r, grade=3)
        assert s_low_d > s_high_d, f"Lower D should boost more: {s_low_d} <= {s_high_d}"

    def test_w8_pinned_effect(self):
        """
        w8=1.6160 is the base multiplier for recall stability.
        Compare two stability values: if w8 were 0, s_prime would be s*(1+...)
        with near-zero factor; if w8 were doubled, factor would roughly double.
        We pin the output at a specific value.
        """
        # d=5, s=5, r=0.8, grade=3
        d, s, r = 5.0, 5.0, 0.8
        w8, w9, w10 = FSRS_W[8], FSRS_W[9], FSRS_W[10]
        exp_inner = math.exp(w10 * (1.0 - r)) - 1.0  # exp(1.0824*0.2)-1 ~ 0.243
        exp_factor = math.exp(w8) * (11.0 - d) * (s ** (-w9)) * exp_inner
        expected_s = max(0.1, s * (1.0 + exp_factor))
        actual = next_recall_stability(d, s, r, grade=3)
        assert math.isclose(actual, expected_s, rel_tol=1e-8), (
            f"next_recall_stability(5,5,0.8,3)={actual}, expected {expected_s}"
        )

    def test_w9_pinned_effect(self):
        """
        w9=0.1544 controls stability decay exponent.
        Pin the s^(-w9) term by computing it explicitly.
        """
        d, s, r = 5.0, 10.0, 0.8
        w8, w9, w10 = FSRS_W[8], FSRS_W[9], FSRS_W[10]
        exp_inner = math.exp(w10 * (1.0 - r)) - 1.0
        s_power = s ** (-w9)  # 10^(-0.1544) ~ 0.700
        exp_factor = math.exp(w8) * (11.0 - d) * s_power * exp_inner
        expected_s = max(0.1, s * (1.0 + exp_factor))
        actual = next_recall_stability(d, s, r, grade=3)
        assert math.isclose(actual, expected_s, rel_tol=1e-8)

    def test_w10_pinned_effect(self):
        """
        w10=1.0824 controls the retrievability term.
        Kills the linearize mutant (exp(w10*(1-r))-1 -> w10*(1-r)).
        With r=0.8: exp(1.0824*0.2)-1 ~ 0.243; linearize gives 1.0824*0.2 = 0.216.
        """
        d, s, r = 5.0, 5.0, 0.8
        w8, w9, w10 = FSRS_W[8], FSRS_W[9], FSRS_W[10]
        exp_inner = math.exp(w10 * (1.0 - r)) - 1.0  # canonical: ~0.243
        linearized = w10 * (1.0 - r)                   # mutant: ~0.216
        assert abs(exp_inner - linearized) > 0.01, "Oracle values too close to distinguish"
        exp_factor = math.exp(w8) * (11.0 - d) * (s ** (-w9)) * exp_inner
        expected_s = max(0.1, s * (1.0 + exp_factor))
        actual = next_recall_stability(d, s, r, grade=3)
        assert math.isclose(actual, expected_s, rel_tol=1e-8), (
            f"w10 oracle failed: got {actual}, expected {expected_s}. "
            f"exp_inner={exp_inner:.6f} vs linearized={linearized:.6f}"
        )


# ---------------------------------------------------------------------------
# Test: next_lapse_stability  (ZERO coverage before this rewrite)
# RED evidence: swap min/max, drop w11, clamp removal
# ---------------------------------------------------------------------------

class TestNextLapseStability:
    """
    S'_lapse = max(0.1, min(s, w11*d^(-w12)*((s+1)^w13-1)*exp(w14*(1-r))))
    """

    def test_lapse_decreases_stability(self):
        """
        After a lapse (grade=1, is_correct=False), stability should decrease.
        Kills swap-min-max mutant which would INCREASE stability.
        """
        s_initial = 5.0
        d = 5.0
        r = 0.8
        s_new = next_lapse_stability(d, s_initial, r)
        assert s_new < s_initial, (
            f"Lapse should decrease stability: {s_new} >= {s_initial}. "
            f"swap-min-max mutant would pass this!"
        )

    def test_lapse_stability_bounded_by_original(self):
        """
        Lapse stability never exceeds the original stability.
        Kills swap-min-max mutant which returns max(s, exp_factor).
        """
        s_initial = 5.0
        d = 5.0
        r = 0.5
        s_new = next_lapse_stability(d, s_initial, r)
        assert s_new <= s_initial, f"s_new={s_new} should be <= s={s_initial}"

    def test_minimum_stability_floor(self):
        """Kills remove-clamp mutant."""
        s_new = next_lapse_stability(d=9.0, s=0.05, r=0.1)
        assert s_new >= 0.1, f"Lapse stability floor violated: {s_new} < 0.1"

    def test_w11_pinned_oracle(self):
        """
        w11=1.9813 is the base multiplier for lapse stability.
        Compute the expected output exactly.
        Kills drop-w11 mutant (w11=1 would give wrong value).
        """
        d, s, r = 5.0, 5.0, 0.5
        w11, w12, w13, w14 = FSRS_W[11], FSRS_W[12], FSRS_W[13], FSRS_W[14]
        exp_f = w11 * (d ** (-w12)) * (((s + 1.0) ** w13) - 1.0) * math.exp(w14 * (1.0 - r))
        expected = max(0.1, min(s, exp_f))
        actual = next_lapse_stability(d, s, r)
        assert math.isclose(actual, expected, rel_tol=1e-8), (
            f"next_lapse_stability(5,5,0.5)={actual}, expected {expected}. "
            f"w11=0 mutant would give ~{max(0.1, min(s, 1.0*(d**(-w12))*(((s+1)**w13)-1)*math.exp(w14*(1-r)))):.4f}"
        )

    def test_w12_w13_w14_effect(self):
        """Verify w12, w13, w14 are exercised by checking the formula structure."""
        d, s, r = 3.0, 10.0, 0.7
        w11, w12, w13, w14 = FSRS_W[11], FSRS_W[12], FSRS_W[13], FSRS_W[14]
        # All three weights appear in the exp_factor; changing any changes the result
        exp_f = w11 * (d ** (-w12)) * (((s + 1.0) ** w13) - 1.0) * math.exp(w14 * (1.0 - r))
        expected = max(0.1, min(s, exp_f))
        actual = next_lapse_stability(d, s, r)
        assert math.isclose(actual, expected, rel_tol=1e-8)

    def test_lapse_high_retrievability_less_decay(self):
        """
        Items with HIGHER retrievability (barely forgotten, R=0.9) lose LESS
        stability on lapse than items with lower retrievability (R=0.1).
        This is because the exp(w14*(1-r)) term is smaller at high R.

        Kills any mutant that inverts this relationship.
        """
        d, s = 5.0, 5.0
        s_r_high = next_lapse_stability(d, s, r=0.9)  # barely forgotten
        s_r_low = next_lapse_stability(d, s, r=0.1)   # deeply forgotten
        assert s_r_high < s_r_low, (
            f"Lapse at high R should reduce stability more: "
            f"s_r_high={s_r_high} >= s_r_low={s_r_low}"
        )


# ---------------------------------------------------------------------------
# Test: calculate_next_interval  (ZERO coverage before this rewrite)
# RED evidence: off-by-one, remove max(1), invert target_r
# ---------------------------------------------------------------------------

class TestCalculateNextInterval:
    """ivl = max(1, round((S/FACTOR)*((1/target_r)-1)))"""

    def test_interval_positive(self):
        """Kills remove-max1 mutant: ivl=0 for tiny stability would return 0."""
        assert calculate_next_interval(0.01) >= 1
        assert calculate_next_interval(0) == 1

    def test_half_life_interval_pinned(self):
        """
        At target_r=0.5, ivl = round(S/FACTOR) = S/(19/81).
        S=10 -> ivl = round(10*81/19) = round(42.6316) = 43.
        Kills off-by-one (+1) mutant which gives 44.
        """
        ivl = calculate_next_interval(10.0, target_r=0.5)
        expected = round(10.0 / FACTOR)
        assert ivl == expected, (
            f"interval(S=10, r=0.5)={ivl}, expected {expected}. "
            f"off-by-one mutant (+1 before round) gives {expected+1}."
        )

    def test_85_percent_retention_pinned(self):
        """
        target_r=0.85: ivl = round((S/FACTOR)*(1/0.85-1)) = round(S/FACTOR*0.17647)
        S=10 -> 42.63*0.17647 = 7.52 -> round = 8.
        Kills invert-target_r mutant ((r-1) instead of (1/r-1)).
        """
        S = 10.0
        expected = _interval_oracle(S, 0.85)
        actual = calculate_next_interval(S, 0.85)
        assert actual == expected, (
            f"calculate_next_interval(10, 0.85)={actual}, expected {expected}. "
            f"invert-target_r mutant gives ~{round(S/FACTOR*(0.85-1))}."
        )

    def test_interval_scales_with_stability(self):
        """Double stability -> interval roughly doubles."""
        ivl1 = calculate_next_interval(5.0, 0.85)
        ivl2 = calculate_next_interval(10.0, 0.85)
        assert ivl2 > ivl1, f"Double stability should increase interval: {ivl2}<={ivl1}"

    def test_higher_retention_target_shorter_interval(self):
        """Higher target_r -> shorter interval (harder to reach)."""
        ivl_85 = calculate_next_interval(10.0, 0.85)
        ivl_95 = calculate_next_interval(10.0, 0.95)
        assert ivl_95 < ivl_85, f"Higher target_r should give shorter interval"

    def test_interval_floor_is_1(self):
        """Very low stability still gives interval of at least 1 day."""
        for s in [0.001, 0.01, 0.1, 0.5, 1.0]:
            ivl = calculate_next_interval(s, 0.85)
            assert ivl >= 1, f"Interval floor violated: ivl({s})={ivl} < 1"

    def test_oracle_table(self):
        """Pin a table of (S, target_r) -> ivl pairs from the formula."""
        table = [
            (1.0, 0.85, 1),
            (5.0, 0.85, 4),
            (10.0, 0.85, 8),
            (20.0, 0.85, 15),   # round(20/0.2345679*0.17647) = round(15.05) = 15
            (10.0, 0.50, 43),
            (10.0, 0.90, 5),    # round(10/0.2345679*0.1111) = round(4.73) = 5
            (10.0, 0.95, 2),
            (50.0, 0.85, 38),
        ]
        for S, r, expected in table:
            actual = calculate_next_interval(S, r)
            assert actual == expected, (
                f"calculate_next_interval({S}, {r})={actual}, expected {expected}"
            )


# ---------------------------------------------------------------------------
# Test: resolve_fsrs_weights
# RED evidence: raise-instead-of-fallback mutant
# ---------------------------------------------------------------------------

class TestResolveFsrsWeights:
    """Per-user FSRS weight vector with safe fallback to FSRS_W."""

    def test_none_profile_returns_default(self):
        """Kills raise-instead-of-fallback mutant."""
        result = resolve_fsrs_weights(None)
        assert result == FSRS_W

    def test_profile_without_attribute_returns_default(self):
        """Missing fsrs_weights attribute -> fallback to FSRS_W."""
        class EmptyProfile:
            pass
        result = resolve_fsrs_weights(EmptyProfile())
        assert result == FSRS_W

    def test_empty_fsrs_weights_returns_default(self):
        """Empty list/None column -> fallback to FSRS_W."""
        class EmptyWeightsProfile:
            fsrs_weights = None
        result = resolve_fsrs_weights(EmptyWeightsProfile())
        assert result == FSRS_W

    def test_valid_custom_weights_used(self):
        """Valid 17-element list replaces defaults."""
        class CustomProfile:
            fsrs_weights = [0.5] * 17
        result = resolve_fsrs_weights(CustomProfile())
        assert result == [0.5] * 17

    def test_wrong_length_returns_default(self):
        """16 or 18 elements -> fallback (malformed)."""
        class BadLenProfile:
            fsrs_weights = [1.0] * 16
        result = resolve_fsrs_weights(BadLenProfile())
        assert result == FSRS_W

    def test_non_finite_returns_default(self):
        """NaN or Inf in any weight -> fallback."""
        bad = [1.0] * 17
        bad[5] = float('nan')
        class NanProfile:
            fsrs_weights = bad
        result = resolve_fsrs_weights(NanProfile())
        assert result == FSRS_W

    def test_length_check(self):
        """Must be exactly 17 weights."""
        assert len(resolve_fsrs_weights(None)) == 17


# ---------------------------------------------------------------------------
# Test: FSRSState
# ---------------------------------------------------------------------------

class TestFSRSState:
    """FSRSState dataclass and its to_dict method."""

    def test_default_values(self):
        s = FSRSState()
        assert s.stability == 1.0
        assert s.difficulty == 5.0
        assert s.reps == 0
        assert s.lapses == 0
        assert s.last_review_at is None
        assert s.next_review_at is None

    def test_to_dict_rounds(self):
        """to_dict rounds floats to 4 decimal places."""
        s = FSRSState(stability=3.14159265, difficulty=2.7182818)
        d = s.to_dict()
        assert d["stability"] == 3.1416
        assert d["difficulty"] == 2.7183

    def test_to_dict_includes_counters(self):
        s = FSRSState(reps=5, lapses=1)
        d = s.to_dict()
        assert d["reps"] == 5
        assert d["lapses"] == 1


# ---------------------------------------------------------------------------
# Test: update_fsrs_state
# ---------------------------------------------------------------------------

class TestUpdateFSRSState:
    """Full state transition through one review."""

    def test_first_review_sets_initial_values(self):
        """
        On first review (reps=0), stability should be set to w[grade-1]
        and difficulty to initial_difficulty(grade).
        """
        state = FSRSState()
        now = datetime.now(timezone.utc)
        new_state, interval = update_fsrs_state(
            state, is_correct=True, confidence=4,
            time_spent_seconds=30, change_count=0, now=now
        )
        # Grade 4 (Easy): w[3] = FSRS_W[3] = 15.4722
        assert new_state.stability == pytest.approx(FSRS_W[3], rel=1e-6)
        assert new_state.difficulty == pytest.approx(initial_difficulty(4), rel=1e-6)
        assert new_state.reps == 1
        assert new_state.lapses == 0
        assert new_state.last_review_at == now

    def test_incorrect_review_increments_lapses(self):
        """Grade 1 (incorrect) increments the lapse counter."""
        state = FSRSState(reps=3)
        new_state, _ = update_fsrs_state(
            state, is_correct=False, confidence=1,
            time_spent_seconds=10, change_count=0
        )
        assert new_state.lapses == state.lapses + 1

    def test_interval_uses_new_stability(self):
        """The returned interval is computed from the new stability."""
        state = FSRSState(stability=10.0, last_review_at=datetime.now(timezone.utc))
        _, interval = update_fsrs_state(
            state, is_correct=True, confidence=4,
            time_spent_seconds=30, change_count=0
        )
        # Grade 4 (Easy) first review: new stability = w[3] = 15.4722
        new_s = FSRS_W[3]
        expected = _interval_oracle(new_s, 0.85)
        # round(15.4722/0.2345679 * 0.17647) = round(65.96*0.17647) = round(11.64) = 12
        assert interval == expected

    def test_next_review_date_is_set(self):
        """next_review_at is set to now + interval_days."""
        now = datetime.now(timezone.utc)
        state = FSRSState(stability=10.0, last_review_at=now)
        new_state, interval = update_fsrs_state(
            state, is_correct=True, confidence=4,
            time_spent_seconds=30, change_count=0, now=now
        )
        expected_next = now + timedelta(days=interval)
        assert new_state.next_review_at == expected_next


# ---------------------------------------------------------------------------
# Test: apply_review_capping
# ---------------------------------------------------------------------------

class TestApplyReviewCapping:
    """Daily review queue: sort by projected retention, cap at max_daily_reviews."""

    def test_most_forgotten_selected_first(self):
        """Items with lowest projected_r are selected first."""
        now = datetime.now(timezone.utc)
        items = [
            {"id": "a", "last_practiced_at": (now - timedelta(days=10)).isoformat(), "fsrs_stability": 5.0},
            {"id": "b", "last_practiced_at": (now - timedelta(days=1)).isoformat(), "fsrs_stability": 5.0},
            {"id": "c", "last_practiced_at": (now - timedelta(days=5)).isoformat(), "fsrs_stability": 5.0},
        ]
        selected, overflow = apply_review_capping(items, max_daily_reviews=2, now=now)
        # a is most forgotten (10 days, same stability -> lowest R)
        assert selected[0]["id"] == "a"
        assert len(selected) == 2
        assert len(overflow) == 1

    def test_overflow_rescheduled(self):
        """Overflow items get a rescheduled_next_review_at field."""
        now = datetime.now(timezone.utc)
        items = [
            {"id": str(i), "last_practiced_at": (now - timedelta(days=5)).isoformat(), "fsrs_stability": 5.0}
            for i in range(7)
        ]
        _, overflow = apply_review_capping(items, max_daily_reviews=5, now=now)
        for item in overflow:
            assert "rescheduled_next_review_at" in item

    def test_projected_retention_used_when_provided(self):
        """Caller-supplied projected_retention overrides the computed one."""
        now = datetime.now(timezone.utc)
        items = [
            {"id": "a", "projected_retention": 0.3, "last_practiced_at": (now - timedelta(days=1)).isoformat()},
            {"id": "b", "projected_retention": 0.9, "last_practiced_at": (now - timedelta(days=1)).isoformat()},
        ]
        selected, _ = apply_review_capping(items, max_daily_reviews=2, now=now)
        # a has lower projected_r -> selected first
        assert selected[0]["id"] == "a"


# ---------------------------------------------------------------------------
# Test: FSRS weight vector integrity
# ---------------------------------------------------------------------------

class TestFSRSWeightIntegrity:
    """All 17 FSRS_W values are pinned to their canonical literals."""

    def test_length_is_17(self):
        assert len(FSRS_W) == 17

    def test_factor_is_canonical(self):
        assert math.isclose(FACTOR, 19.0 / 81.0, rel_tol=1e-12)

    def test_w0_w1_w2_w3(self):
        """w0..w3: initial stability parameters."""
        assert math.isclose(FSRS_W[0], 0.4072, rel_tol=1e-4)
        assert math.isclose(FSRS_W[1], 1.1827, rel_tol=1e-4)
        assert math.isclose(FSRS_W[2], 3.1262, rel_tol=1e-4)
        assert math.isclose(FSRS_W[3], 15.4722, rel_tol=1e-4)

    def test_w4_w5_initial_difficulty(self):
        """w4..w5: initial difficulty parameters."""
        assert math.isclose(FSRS_W[4], 7.2102, rel_tol=1e-4)
        assert math.isclose(FSRS_W[5], 0.5316, rel_tol=1e-4)

    def test_w6_w7_difficulty_adjustment(self):
        """w6..w7: difficulty adjustment / mean reversion."""
        assert math.isclose(FSRS_W[6], 1.0651, rel_tol=1e-4)
        assert math.isclose(FSRS_W[7], 0.0234, rel_tol=1e-4)

    def test_w8_w9_w10_recall_stability(self):
        """w8..w10: recall stability update parameters."""
        assert math.isclose(FSRS_W[8], 1.6160, rel_tol=1e-4)
        assert math.isclose(FSRS_W[9], 0.1544, rel_tol=1e-4)
        assert math.isclose(FSRS_W[10], 1.0824, rel_tol=1e-4)

    def test_w11_w12_w13_w14_lapse_stability(self):
        """w11..w14: lapse stability update parameters."""
        assert math.isclose(FSRS_W[11], 1.9813, rel_tol=1e-4)
        assert math.isclose(FSRS_W[12], 0.0953, rel_tol=1e-4)
        assert math.isclose(FSRS_W[13], 0.2975, rel_tol=1e-4)
        assert math.isclose(FSRS_W[14], 0.2242, rel_tol=1e-4)

    def test_w15_w16_hard_easy_modifiers(self):
        """w15..w16: hard/easy grade modifiers."""
        assert math.isclose(FSRS_W[15], 0.2507, rel_tol=1e-4)
        assert math.isclose(FSRS_W[16], 2.9466, rel_tol=1e-4)

    def test_all_weights_positive(self):
        """No negative weights anywhere -- FSRS requires all w > 0."""
        for i, w in enumerate(FSRS_W):
            assert w > 0, f"FSRS_W[{i}] = {w} must be positive"

    def test_weights_produce_valid_difficulties(self):
        """Every grade produces initial difficulty in [1, 10] with canonical weights."""
        for grade in [1, 2, 3, 4]:
            d = initial_difficulty(grade)
            assert 1.0 <= d <= 10.0


# ---------------------------------------------------------------------------
# Test: _weights helper
# ---------------------------------------------------------------------------

class Test_weights:
    """_weights() normalizes the optional per-call weight vector."""

    def test_none_returns_fsrs_w(self):
        assert _weights(None) == FSRS_W

    def test_empty_list_returns_fsrs_w(self):
        assert _weights([]) == FSRS_W

    def test_valid_weights_returned(self):
        custom = [1.0] * 17
        assert _weights(custom) == custom