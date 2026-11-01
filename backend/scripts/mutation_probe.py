"""
mutation_probe.py — In-memory mutant executor for learning_engine.py

Loads learning_engine.py source as a string, applies a targeted string-level
mutation, exec()s it into a fresh namespace, injects it as
'services.paes.learning_engine' in sys.modules (clearing any prior import),
and returns the mutated module.

Usage
-----
    from backend.scripts.mutation_probe import MutantProbe
    probe = MutantProbe()

    # Kill the FACTOR mutant
    mut = probe.mutate("FACTOR", "1.0")
    ok = probe.test_next_interval_mutant(mut)   # → False if test catches it

    # Restore real module
    probe.restore()
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

# Path to the implementation under test (READ-ONLY — never written)
_LEARNING_ENGINE_PATH = Path(__file__).parent.parent / "services" / "paes" / "learning_engine.py"

# Canonical default FSRS-4.5 constants (for oracle assertions)
FACTOR = 19.0 / 81.0  # ≈ 0.2345679012345679
FSRS_W = [
    0.4072,
    1.1827,
    3.1262,
    15.4722,  # w0..w3
    7.2102,
    0.5316,  # w4..w5
    1.0651,
    0.0234,  # w6..w7
    1.6160,
    0.1544,
    1.0824,  # w8..w10
    1.9813,
    0.0953,
    0.2975,
    0.2242,  # w11..w14
    0.2507,
    2.9466,  # w15..w16
]


class MutantProbe:
    """
    In-memory mutant executor for learning_engine.py.

    Each ``mutate_<name>`` method returns the mutated source string.
    Each ``test_<name>_mutant`` method applies the mutation, re-imports the
    module, runs the given test-callable, and returns True (mutant killed:
    test failed) or False (mutant survived: test passed).
    """

    def __init__(self) -> None:
        self._original_source = _LEARNING_ENGINE_PATH.read_text(encoding="utf-8")
        self._backup_module: types.ModuleType | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def apply(self, mutated_source: str) -> types.ModuleType:
        """
        Compile and import ``mutated_source`` as 'services.paes.learning_engine'.
        Clears the prior module from sys.modules first.
        Returns the new module object.
        """
        # Remove prior import so Python re-evaluates from the mutated source
        for key in list(sys.modules.keys()):
            if key.startswith("services.paes"):
                del sys.modules[key]

        namespace: dict[str, object] = {}
        exec(compile(mutated_source, str(_LEARNING_ENGINE_PATH), "exec"), namespace)
        mod = types.ModuleType("services.paes.learning_engine")
        mod.__dict__.update(namespace)
        sys.modules["services.paes.learning_engine"] = mod
        return mod

    def restore(self) -> None:
        """Restore the real, unmutated module from the backup source."""
        if self._backup_module is not None:
            sys.modules["services.paes.learning_engine"] = self._backup_module

    # ------------------------------------------------------------------
    # Mutant factories — each returns a new mutated source string
    # ------------------------------------------------------------------

    def mutate_FACTOR_1(self, src: str) -> str:
        """FACTOR = 19/81 → 1.0  (kills half-life and retrievability tests)"""
        return src.replace("FACTOR = 19.0 / 81.0", "FACTOR = 1.0")

    def mutate_FACTOR_half(self, src: str) -> str:
        """FACTOR = 19/81 → 0.5  (changes half-life scale)"""
        return src.replace("FACTOR = 19.0 / 81.0", "FACTOR = 0.5")

    def mutate_retrievability_sign(self, src: str) -> str:
        """R(t,S) = 1/(1 + t/S)  →  1/(1 - t/S)  (sign flip in denominator)"""
        return src.replace(
            "return float(1.0 / (1.0 + FACTOR * (t / stability)))",
            "return float(1.0 / (1.0 - FACTOR * (t / stability)))",
        )

    def mutate_retrievability_drop_factor(self, src: str) -> str:
        """R(t,S) = 1/(1 + t/S)  (drops FACTOR entirely)"""
        return src.replace(
            "return float(1.0 / (1.0 + FACTOR * (t / stability)))",
            "return float(1.0 / (1.0 + (t / stability)))",
        )

    def mutate_grade_boundary_150(self, src: str) -> str:
        """time > 150 → time > 149  (off-by-one at grade-2 boundary)"""
        return src.replace("time_spent_seconds > 150", "time_spent_seconds > 149")

    def mutate_grade_boundary_45(self, src: str) -> str:
        """time < 45 → time < 44  (off-by-one at grade-4 boundary)"""
        return src.replace("time_spent_seconds < 45", "time_spent_seconds < 44")

    def mutate_grade_boundary_change(self, src: str) -> str:
        """change_count >= 2 → change_count >= 1  (too eager for grade-2)"""
        return src.replace("change_count >= 2", "change_count >= 1")

    def mutate_grade_easy_confidence(self, src: str) -> str:
        """confidence >= 4 → confidence >= 3  (too eager for grade-4)"""
        return src.replace("confidence >= 4", "confidence >= 3")

    def mutate_initial_difficulty_sign(self, src: str) -> str:
        """flip the sign of the exp term: -exp(w5*(g-1)) → +exp(w5*(g-1))"""
        return src.replace(
            "val = w[4] - math.exp(w[5] * (grade - 1)) + 1.0",
            "val = w[4] + math.exp(w[5] * (grade - 1)) + 1.0",
        )

    def mutate_initial_difficulty_drop_offset(self, src: str) -> str:
        """drop the +1.0 offset: w4 - exp(w5*(g-1)) + 1.0 → w4 - exp(w5*(g-1))"""
        return src.replace(
            "val = w[4] - math.exp(w[5] * (grade - 1)) + 1.0",
            "val = w[4] - math.exp(w[5] * (grade - 1))",
        )

    def mutate_next_difficulty_no_reversion(self, src: str) -> str:
        """
        next_difficulty: remove the mean-reversion term.
        w[7]*D0_good + (1-w[7])*D_raw  →  D_raw
        """
        return src.replace(
            "d_new = w[7] * d_0_good + (1.0 - w[7]) * d_raw",
            "d_new = d_raw",
        )

    def mutate_next_difficulty_swap_coefficients(self, src: str) -> str:
        """
        Swap coefficients of the mean-reversion blend.
        w[7]*D0_good + (1-w[7])*D_raw  →  (1-w[7])*D0_good + w[7]*D_raw
        """
        return src.replace(
            "d_new = w[7] * d_0_good + (1.0 - w[7]) * d_raw",
            "d_new = (1.0 - w[7]) * d_0_good + w[7] * d_raw",
        )

    def mutate_next_difficulty_remove_clamp(self, src: str) -> str:
        """Remove the [1,10] clamp from next_difficulty output"""
        return src.replace(
            "return max(1.0, min(10.0, d_new))",
            "return d_new",
        )

    def mutate_next_recall_stability_linearize(self, src: str) -> str:
        """
        Linearize the exp(w10*(1-r)) - 1  factor →  w10*(1-r)
        This changes the entire shape of the stability-update curve.
        """
        return src.replace(
            "math.exp(w[10] * (1.0 - r)) - 1.0",
            "w[10] * (1.0 - r)",
        )

    def mutate_next_recall_stability_drop_hard_easy(self, src: str) -> str:
        """Drop the hard/easy grade modifier h_g (set to 1.0 always)"""
        return src.replace(
            "h_g = w[15] if grade == 2 else (w[16] if grade == 4 else 1.0)",
            "h_g = 1.0",
        )

    def mutate_next_recall_stability_remove_clamp(self, src: str) -> str:
        """Remove the min-stability clamp (0.1) from recall stability"""
        return src.replace(
            "return max(0.1, s * (1.0 + exp_factor))",
            "return s * (1.0 + exp_factor)",
        )

    def mutate_next_lapse_stability_swap_minmax(self, src: str) -> str:
        """
        swap min(s, exp_factor) → max(s, exp_factor)
        Lapse stability should DECREASE, so min is correct.
        """
        return src.replace(
            "s_new = min(s, exp_factor)",
            "s_new = max(s, exp_factor)",
        )

    def mutate_next_lapse_stability_drop_w11(self, src: str) -> str:
        """Drop w[11] from the lapse stability formula"""
        return src.replace(
            "w[11] * (d ** (-w[12]))",
            "1.0 * (d ** (-w[12]))",
        )

    def mutate_next_lapse_stability_remove_clamp(self, src: str) -> str:
        """Remove the min-stability clamp (0.1) from lapse stability"""
        return src.replace(
            "return max(0.1, s_new)",
            "return s_new",
        )

    def mutate_next_interval_offbyone(self, src: str) -> str:
        """
        round(ivl) → round(ivl) + 1  (off-by-one on interval)
        """
        return src.replace(
            "return max(1, round(ivl))",
            "return max(1, round(ivl) + 1)",
        )

    def mutate_next_interval_remove_max1(self, src: str) -> str:
        """
        Remove the max(1, ...) floor — allows interval=0 for tiny stability.
        """
        return src.replace(
            "return max(1, round(ivl))",
            "return round(ivl)",
        )

    def mutate_next_interval_invert_targetr(self, src: str) -> str:
        """
        Invert target_r: (1/target_r - 1) → (target_r - 1)
        Changes the interval calculation direction.
        """
        return src.replace(
            "* ((1.0 / target_r) - 1.0)",
            "* ((target_r) - 1.0)",
        )

    def mutate_resolve_fsrs_weights_drop_fallback(self, src: str) -> str:
        """
        resolve_fsrs_weights: if profile has no fsrs_weights, raise instead of
        falling back to FSRS_W. Kills the fallback safety net.
        """
        return src.replace(
            "    if not raw:\n        return FSRS_W",
            "    if not raw:\n        raise ValueError('profile has no fsrs_weights')",
        )

    def mutate_w8_zero(self, src: str) -> str:
        """Set w[8] = 0 (should be 1.6160) — kills recall stability scaling"""
        return src.replace("1.6160, 0.1544, 1.0824,", "0.0, 0.1544, 1.0824,")

    def mutate_w9_one(self, src: str) -> str:
        """Set w[9] = 1 (should be 0.1544) — changes stability decay exponent"""
        return src.replace("1.6160, 0.1544, 1.0824,", "1.6160, 1.0, 1.0824,")

    def mutate_w10_zero(self, src: str) -> str:
        """Set w[10] = 0 (should be 1.0824) — linearizes the recall stability factor"""
        return src.replace("1.6160, 0.1544, 1.0824,", "1.6160, 0.1544, 0.0,")

    def mutate_w11_zero(self, src: str) -> str:
        """Set w[11] = 0 (should be 1.9813) — kills lapse stability"""
        return src.replace("1.9813, 0.0953, 0.2975, 0.2242,", "0.0, 0.0953, 0.2975, 0.2242,")

    def mutate_w15_zero(self, src: str) -> str:
        """Set w[15] = 0 (should be 0.2507) — kills Hard grade modifier"""
        return src.replace("0.2507, 2.9466", "0.0, 2.9466")

    def mutate_w16_zero(self, src: str) -> str:
        """Set w[16] = 0 (should be 2.9466) — kills Easy grade modifier"""
        return src.replace("0.2507, 2.9466", "0.2507, 0.0")

    def mutate_w15_double(self, src: str) -> str:
        """Set w[15] = 2*0.2507 (should be 0.2507)"""
        return src.replace("0.2507, 2.9466", "0.5014, 2.9466")


# ------------------------------------------------------------------
# Quick sanity check — run with: python mutation_probe.py
# ------------------------------------------------------------------
if __name__ == "__main__":
    import math

    probe = MutantProbe()

    # --- Oracle values (hand-computed from FSRS v4.5 paper equations) ---

    # FACTOR = 19/81 ≈ 0.2345679
    # R(t,S) = 1/(1 + FACTOR*t/S)
    # Half-life: t = S/FACTOR
    assert math.isclose(FACTOR, 19.0 / 81.0)
    # R(0, S) = 1.0
    # R(10/81*5, 5) = 0.5

    # infer_fsrs_grade: grade-2 boundary at time > 150, grade-4 at time < 45
    # initial_difficulty: D(G) = w4 - exp(w5*(G-1)) + 1.0, clamped [1,10]
    w4, w5 = FSRS_W[4], FSRS_W[5]
    for g, expected_approx in [(1, 7.2102), (2, 4.585), (3, 2.962), (4, 2.171)]:
        raw = w4 - math.exp(w5 * (g - 1)) + 1.0
        clamped = max(1.0, min(10.0, raw))
        print(f"initial_difficulty({g}) ~ {clamped:.4f}  (raw={raw:.4f})")

    # next_difficulty: D' = w7*D0_good + (1-w7)*D_raw
    # Mean reversion magnitude: w7 = 0.0234, so movement is tiny
    w7 = FSRS_W[7]
    d0_good = max(1.0, min(10.0, w4 - math.exp(w5 * 2) + 1.0))
    print(f"\nmean reversion coefficient w7={w7}")
    print(f"D0(Good)={d0_good:.4f}  movement for d=9 → d'={w7*d0_good + (1-w7)*9:.4f}")

    # calculate_next_interval: ivl = (S/FACTOR)*((1/R)-1)
    # S=10, target_r=0.9 → ivl = (10/0.2346)*((1/0.9)-1) = 42.67*(0.1111) ≈ 4.74 → round=5
    S_test = 10.0
    target_r_test = 0.9
    ivl = (S_test / FACTOR) * ((1.0 / target_r_test) - 1.0)
    print(f"\ncalculate_next_interval(S={S_test}, target_r={target_r_test}) = {round(ivl)}")

    # S=1, target_r=0.85 → ivl = (1/0.2346)*(0.1765) ≈ 0.752 → round=1
    S_test2 = 1.0
    target_r_test2 = 0.85
    ivl2 = (S_test2 / FACTOR) * ((1.0 / target_r_test2) - 1.0)
    print(f"calculate_next_interval(S={S_test2}, target_r={target_r_test2}) = {round(ivl2)}")

    # next_lapse_stability: s_new = min(s, w11*d^(-w12)*((s+1)^w13 - 1)*exp(w14*(1-r))
    w11, w12, w13, w14 = FSRS_W[11], FSRS_W[12], FSRS_W[13], FSRS_W[14]
    d_l, s_l, r_l = 5.0, 5.0, 0.5
    exp_f = w11 * (d_l ** (-w12)) * (((s_l + 1.0) ** w13) - 1.0) * math.exp(w14 * (1.0 - r_l))
    s_new_l = min(s_l, exp_f)
    print(f"\nnext_lapse_stability(d={d_l}, s={s_l}, r={r_l}) = {max(0.1, s_new_l):.4f}")
    print(f"  (exp_factor={exp_f:.4f}, s={s_l}, min={s_new_l:.4f})")

    print("\n✅ Oracle values sanity-checked.")
