"""Regression tests: AI prompt strings must use neutral Spanish, not voseo."""

import ast
import re
from pathlib import Path

from pydantic import BaseModel

BACKEND_ROOT = Path(__file__).resolve().parents[1]

# Conservative list of Rioplatense voseo imperatives/inflections. Neutral
# tuteo forms (e.g. "incluye", "asegúrate", "marca") deliberately do not match.
BANNED_VOSEO_TOKENS = (
    "incluí",
    "adaptá",
    "asegurate",
    "asegurá",
    "corregí",
    "devolvé",
    "devolve",
    "exigi",
    "exigí",
    "marcá",
    "consultá",
    "intentá",
    "generá",
    "elegí",
    "escribí",
    "explicá",
    "mostrá",
    "pensá",
    "revisá",
    "esforzate",
    "concentrate",
    "fijate",
    "acordate",
    "ponele",
    "decime",
    "andá",
    "mirá",
    "hacé",
    "usá",
    "decile",
    "pedile",
    "contame",
    "explicame",
    "ayudame",
    "hacelo",
    "dalo",
    "dejá",
    "pasá",
    "llamá",
    "tomá",
    "buscá",
    "sacá",
    "poné",
    "tenés",
    "podés",
    "sabés",
    "querés",
    "preferís",
    "vivís",
    "sos",
    "vos",
    "pibe",
    "laburo",
    "che",
)

# Legitimate occurrences that are not Rioplatense voseo must be listed here
# as (relative_path, token): justification. Keep this list empty unless a
# genuine false positive is proven.
ALLOWLIST: dict[tuple[str, str], str] = {}

# The mandatory language rule itself enumerates the banned tokens, so that
# literal must be exempt from the scan. This marker only appears in such rules.
ALLOWED_LITERAL_MARKERS = ("prohibido:",)

_VOSEO_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(token) for token in BANNED_VOSEO_TOKENS) + r")\b",
    re.IGNORECASE,
)


class _Probe(BaseModel):
    ok: bool


def _scan_paths() -> list[Path]:
    paths = sorted((BACKEND_ROOT / "core").glob("*.py"))
    paths += sorted((BACKEND_ROOT / "services").rglob("*.py"))
    return paths


def _iter_string_literals(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            yield node.lineno, node.value


def test_augmented_system_prompt_includes_neutral_spanish_rule():
    from core.router import _build_augmented_system

    augmented = _build_augmented_system("Eres un tutor.", _Probe)

    assert "español neutro" in augmented
    assert "voseo" in augmented
    assert "IDIOMA (OBLIGATORIO)" in augmented
    assert augmented.count("IDIOMA (OBLIGATORIO)") == 1


def test_augmented_system_prompt_does_not_duplicate_existing_rule():
    from core.router import _build_augmented_system

    prompt = "Eres un tutor. IDIOMA (OBLIGATORIO): español neutro de Chile."
    augmented = _build_augmented_system(prompt, _Probe)

    assert augmented.count("IDIOMA (OBLIGATORIO)") == 1


def test_coach_system_prompt_includes_neutral_spanish_rule():
    from api.routes.coach import _get_coach_system_prompt

    prompt = _get_coach_system_prompt()

    assert "español neutro" in prompt
    assert "voseo" in prompt


def test_prompt_strings_do_not_contain_voseo():
    violations = []

    for path in _scan_paths():
        rel_path = path.relative_to(BACKEND_ROOT).as_posix()
        for start_line, text in _iter_string_literals(path):
            if any(marker in text for marker in ALLOWED_LITERAL_MARKERS):
                continue
            for match in _VOSEO_RE.finditer(text):
                token = match.group(0).lower()
                if (rel_path, token) in ALLOWLIST:
                    continue
                line = start_line + text[: match.start()].count("\n")
                snippet = " ".join(text.split())[:100]
                violations.append(f"{rel_path}:{line}: {token!r} in {snippet!r}")

    assert not violations, "Voseo found in prompt/instruction strings:\n" + "\n".join(violations)
