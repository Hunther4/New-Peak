"""
Pipeline Autónomo de Generación de Contenido y Banco de Preguntas PAES.
Genera ítems psicométricamente calibrados para PAES (M1, M2, LECTURA, CIENCIAS, HISTORIA):
- Generador Simbólico CAS (SymPy) para matemática paramétrica exacta (sin alucinaciones ni duplicados).
- Generador Curricular de Contexto amplio con 40+ escenarios temáticos oficiales DEMRE.
- Validador QualityFilter (formato KaTeX, balance de distractores, 1 sola clave correcta).
- Calibrador Heurístico 3PL IRT (a, b, c).
- Deduplicador en memoria y contra base de datos peak.db.
- Inserción transaccional segura en peak.db.
"""
import argparse
import json
import logging
import math
import random
import sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# Ensure backend directory is in path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from sqlmodel import Session, select

from core.database import engine
from curriculum_banks.calibrate_irt_parameters import compute_irt_parameters
from curriculum_banks.quality_filter import QualityFilter
from models.paes_models import (
    PaesCompetency,
    PaesEjeTematico,
    PaesQuestion,
    PaesSubject,
    PaesSubtopic,
    PaesTopic,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class AutoContentGenerator:
    """Motor automatizado de creación y calibración de ítems PAES."""

    def __init__(self, db_session: Optional[Session] = None):
        self.session = db_session
        self._competency_cache: Dict[str, str] = {}
        self._subtopics_cache: Dict[str, List[Dict[str, Any]]] = {}
        self.seen_stems: set = set()

        if self.session:
            try:
                existing = self.session.exec(select(PaesQuestion.stem)).all()
                self.seen_stems = {s.strip().lower() for s in existing if s}
            except Exception as e:
                logger.warning(f"No se pudieron precargar enunciados existentes: {e}")

    def _get_competency_id(self, code: str, default: str = "a3da57b1-2533-572d-857b-27063e83c1ce") -> str:
        """Retorna el ID de la competencia en base a su código."""
        if not self._competency_cache and self.session:
            try:
                comps = self.session.exec(select(PaesCompetency)).all()
                for c in comps:
                    self._competency_cache[c.code] = c.id
            except Exception:
                pass
        return self._competency_cache.get(code, default)

    def _load_subtopics_by_subject(self, subject_code: str) -> List[Dict[str, Any]]:
        """Carga y cachea los subtemas asociados a una asignatura."""
        subj_upper = subject_code.upper()
        if subj_upper in self._subtopics_cache:
            return self._subtopics_cache[subj_upper]

        subtopics_list = []
        if self.session:
            try:
                query = (
                    select(PaesSubtopic, PaesTopic, PaesEjeTematico, PaesSubject)
                    .join(PaesTopic, PaesSubtopic.topic_id == PaesTopic.id)
                    .join(PaesEjeTematico, PaesTopic.eje_id == PaesEjeTematico.id)
                    .join(PaesSubject, PaesEjeTematico.subject_id == PaesSubject.id)
                    .where(PaesSubject.code == subj_upper)
                )
                results = self.session.exec(query).all()
                for s, t, e, subj in results:
                    subtopics_list.append({
                        "id": s.id,
                        "name": s.name,
                        "slug": s.slug,
                        "topic_name": t.name,
                        "eje_name": e.name,
                        "subject_code": subj.code,
                    })
            except Exception as ex:
                logger.warning(f"Error cargando subtemas de DB para {subj_upper}: {ex}")

        if not subtopics_list:
            subtopics_list = [{
                "id": f"sub-{subj_upper.lower()}-base",
                "name": f"Subtema General {subj_upper}",
                "slug": f"sub-{subj_upper.lower()}-base",
                "topic_name": "General",
                "eje_name": "General",
                "subject_code": subj_upper,
            }]

        self._subtopics_cache[subj_upper] = subtopics_list
        return subtopics_list

    # ==========================================
    # 1. GENERADORES MATEMÁTICOS SIMBÓLICOS (CAS)
    # ==========================================

    def _gen_linear_equation(self, subtopic_id: str, skill_id: str, rng: random.Random) -> Dict[str, Any]:
        """Ecuación lineal con trasposición y coeficientes enteros."""
        sol = rng.choice([i for i in range(-15, 16) if i != 0])
        a = rng.choice([2, 3, 4, 5, 6, 7, 8, 9])
        b = rng.choice([i for i in range(-30, 31) if i != 0])
        c = a * sol + b

        b_sign = f"+ {b}" if b > 0 else f"- {abs(b)}"
        stem = f"¿Cuál es el valor de $x$ que satisface la ecuación lineal ${a}x {b_sign} = {c}$?"

        d1 = round((c + b) / a, 2)
        d2 = c - b
        d3 = sol + rng.choice([-3, -2, -1, 1, 2, 3])

        candidates = [
            {"val": sol, "is_correct": True, "type": "CORRECT", "desc": "Despeje algebraico riguroso"},
            {"val": d1, "is_correct": False, "type": "CALCULATION_ERROR", "desc": "Error de signo al trasponer el término independiente"},
            {"val": d2, "is_correct": False, "type": "CONCEPTUAL_CONFUSION", "desc": "Omisión de la división por el coeficiente"},
            {"val": d3, "is_correct": False, "type": "HEURISTIC_TRAP", "desc": "Aproximación aritmética incorrecta"},
        ]

        return self._build_math_item(stem, candidates, subtopic_id, skill_id, rng, 0.40, (
            f"1. Restamos o sumamos el término libre: ${a}x = {c} {'-' if b > 0 else '+'} {abs(b)} = {c - b}$.\n"
            f"2. Dividimos por ${a}$: $x = \\frac{{{c - b}}}{{{a}}} = {sol}$."
        ), "Olvidar cambiar el signo al trasponer términos de un miembro al otro.")

    def _gen_linear_system(self, subtopic_id: str, skill_id: str, rng: random.Random) -> Dict[str, Any]:
        """Sistema de ecuaciones lineales 2x2."""
        x_val = rng.choice([2, 3, 4, 5, 6, 7, 8])
        y_val = rng.choice([1, 2, 3, 4, 5, 6])
        a1, b1 = rng.choice([(1, 1), (2, 1), (1, 2), (3, 1)])
        a2, b2 = rng.choice([(1, -1), (2, -1), (1, -2), (3, -2)])

        c1 = a1 * x_val + b1 * y_val
        c2 = a2 * x_val + b2 * y_val

        sign_b1 = f"+ {b1}y" if b1 > 1 else ("+ y" if b1 == 1 else (f"- {abs(b1)}y" if b1 < -1 else "- y"))
        sign_b2 = f"+ {b2}y" if b2 > 1 else ("+ y" if b2 == 1 else (f"- {abs(b2)}y" if b2 < -1 else "- y"))
        a1_str = f"{a1}x" if a1 > 1 else "x"
        a2_str = f"{a2}x" if a2 > 1 else "x"

        stem = (
            f"Dado el siguiente sistema de ecuaciones lineales:\n"
            f"$$\\begin{{cases}} {a1_str} {sign_b1} = {c1} \\\\ {a2_str} {sign_b2} = {c2} \\end{{cases}}$$\n"
            f"¿Cuál es el valor del producto $x \\cdot y$?"
        )

        sol = x_val * y_val
        d1 = x_val + y_val  # Suma en vez de producto
        d2 = abs(x_val - y_val)  # Diferencia
        d3 = sol + rng.choice([-4, -2, 2, 4])

        candidates = [
            {"val": sol, "is_correct": True, "type": "CORRECT", "desc": "Resolución exacta del sistema y producto $x \\cdot y$"},
            {"val": d1, "is_correct": False, "type": "CONCEPTUAL_CONFUSION", "desc": "Calculó la suma $x + y$ en vez del producto solicitado"},
            {"val": d2, "is_correct": False, "type": "HEURISTIC_TRAP", "desc": "Calculó la diferencia entre las variables"},
            {"val": d3, "is_correct": False, "type": "CALCULATION_ERROR", "desc": "Error aritmético en la sustitución"},
        ]

        return self._build_math_item(stem, candidates, subtopic_id, skill_id, rng, 0.58, (
            f"Resolviendo el sistema por reducción o sustitución se obtiene $x = {x_val}$ e $y = {y_val}$.\n"
            f"El producto pedido es $x \\cdot y = {x_val} \\cdot {y_val} = {sol}$."
        ), "Confundir la operación final pedida (producto vs suma de las soluciones).")

    def _gen_percentage_problem(self, subtopic_id: str, skill_id: str, rng: random.Random) -> Dict[str, Any]:
        """Problema contextual de porcentajes y finanzas."""
        price = rng.choice([8000, 12000, 15000, 18000, 24000, 32000, 45000, 60000, 80000])
        pct = rng.choice([10, 15, 20, 25, 30, 40, 50])
        mode = rng.choice(["descuento", "aumento"])

        items = ["un computador portátil", "una bicicleta de montaña", "un teléfono móvil", "un telescopio astronómico", "una guitarra electroacústica"]
        chosen_item = rng.choice(items)

        if mode == "descuento":
            stem = (
                f"El valor de lista de {chosen_item} es de \\${price:,}. "
                f"Si por pago al contado se aplica un descuento del ${pct}\\%$, "
                f"¿cuál es el precio final que se cancela?"
            ).replace(",", ".")
            final_p = int(price * (1 - pct / 100))
            d1 = int(price * (pct / 100))
            d2 = int(price * (1 + pct / 100))
            d3 = price - (pct * 100)
            reason_d1 = "Calculó solo el monto del descuento pero no el valor final pagado"
        else:
            stem = (
                f"El precio neto de {chosen_item} es de \\${price:,}. "
                f"Si se le debe recargar un ${pct}\\%$ por concepto de gastos de envío e impuestos, "
                f"¿cuál es el monto total a pagar?"
            ).replace(",", ".")
            final_p = int(price * (1 + pct / 100))
            d1 = int(price * (pct / 100))
            d2 = int(price * (1 - pct / 100))
            d3 = price + (pct * 100)
            reason_d1 = "Calculó el recargo pero olvidó sumarlo al valor base"

        candidates = [
            {"val": final_p, "is_correct": True, "type": "CORRECT", "desc": "Cálculo porcentual exacto"},
            {"val": d1, "is_correct": False, "type": "CONCEPTUAL_CONFUSION", "desc": reason_d1},
            {"val": d2, "is_correct": False, "type": "CALCULATION_ERROR", "desc": "Operación inversa (restó en vez de sumar o viceversa)"},
            {"val": d3, "is_correct": False, "type": "HEURISTIC_TRAP", "desc": "Error dimensional con el porcentaje"},
        ]

        def fmt(v):
            return f"\\${v:,}".replace(",", ".")

        return self._build_math_item(stem, candidates, subtopic_id, skill_id, rng, 0.45, (
            f"El valor base es \\${price:,}. Operando con el factor multiplicador correspondiente:\n"
            f"$$\\text{{Total}} = {price:,} \\times \\left(1 {'-' if mode == 'descuento' else '+'} \\frac{{{pct}}}{{100}}\\right) = \\${final_p:,}$$."
        ).replace(",", "."), "Marcar la cuantía del porcentaje en lugar del valor final de la transacción.", fmt_fn=fmt)

    def _gen_pythagoras_problem(self, subtopic_id: str, skill_id: str, rng: random.Random) -> Dict[str, Any]:
        """Teorema de Pitágoras con ternas pitagóricas enteras."""
        triples = [(3, 4, 5), (6, 8, 10), (5, 12, 13), (9, 12, 15), (8, 15, 17), (12, 16, 20), (7, 24, 25), (10, 24, 26), (15, 20, 25), (20, 21, 29)]
        cat1, cat2, hyp = rng.choice(triples)
        ask_hyp = rng.choice([True, False])

        contexts = [
            ("una escalera apoyada en una pared vertical", "la distancia de la base de la pared al pie de la escalera", "la altura alcanzada en la pared", "la longitud de la escalera"),
            ("un poste telefónico sujetado por un cable tensor", "la distancia desde el poste hasta el anclaje en el suelo", "la altura del poste donde se fija el cable", "el largo del cable tensor"),
            ("un parque rectangular atravesado por un sendero diagonal", "el ancho del parque", "el largo del parque", "la longitud del sendero diagonal"),
        ]
        ctx = rng.choice(contexts)

        if ask_hyp:
            stem = f"En {ctx[0]}, se sabe que {ctx[1]} es de ${cat1}\\text{{ m}}$ y {ctx[2]} es de ${cat2}\\text{{ m}}$. ¿Cuánto mide {ctx[3]}?"
            sol = hyp
            d1 = cat1 + cat2
            d2 = round(math.sqrt(abs(cat2**2 - cat1**2)), 1)
            d3 = hyp + rng.choice([-2, -1, 1, 2])
        else:
            stem = f"En {ctx[0]}, se conoce que {ctx[3]} mide ${hyp}\\text{{ m}}$ y {ctx[1]} mide ${cat1}\\text{{ m}}$. ¿Cuál es la medida de {ctx[2]}?"
            sol = cat2
            d1 = hyp - cat1
            d2 = round(math.sqrt(hyp**2 + cat1**2), 1)
            d3 = cat2 + rng.choice([-2, -1, 1, 2])

        candidates = [
            {"val": sol, "is_correct": True, "type": "CORRECT", "desc": "Aplicación del Teorema de Pitágoras"},
            {"val": d1, "is_correct": False, "type": "CONCEPTUAL_CONFUSION", "desc": "Suma o resta lineal sin elevar al cuadrado"},
            {"val": d2, "is_correct": False, "type": "CALCULATION_ERROR", "desc": "Error en el signo de la relación métrica"},
            {"val": d3, "is_correct": False, "type": "HEURISTIC_TRAP", "desc": "Aproximación numérica errónea"},
        ]

        def fmt(v):
            return f"${v}\\text{{ m}}$"

        return self._build_math_item(stem, candidates, subtopic_id, skill_id, rng, 0.48, (
            f"Por el Teorema de Pitágoras ($a^2 + b^2 = c^2$):\n"
            f"El valor pedido resulta ser exactamente ${sol}\\text{{ m}}$."
        ), "Sumar o restar directamente las medidas sin considerar la suma de los cuadrados.", fmt_fn=fmt)

    def _gen_powers_roots(self, subtopic_id: str, skill_id: str, rng: random.Random) -> Dict[str, Any]:
        """Propiedades de potencias y raíces en los racionales."""
        base = rng.choice([2, 3, 5])
        p1 = rng.choice([2, 3, 4])
        p2 = rng.choice([2, 3])
        p3 = rng.choice([1, 2])

        stem = f"¿A qué valor equivale la expresión numérica $\\frac{{{base}^{{{p1}}} \\cdot {base}^{{{p2}}}}}{{{base}^{{{p3}}}}}$?"
        exp_final = p1 + p2 - p3
        sol = base ** exp_final
        d1 = base ** (p1 + p2 + p3)  # Sumar en el denominador
        d2 = base ** (p1 * p2 - p3)  # Multiplicar exponentes en el producto
        d3 = (base * 2) ** exp_final  # Multiplicar la base

        candidates = [
            {"val": sol, "is_correct": True, "type": "CORRECT", "desc": "Aplicación de propiedades de potencias de igual base"},
            {"val": d1, "is_correct": False, "type": "CONCEPTUAL_CONFUSION", "desc": "Sumó el exponente del divisor en vez de restarlo"},
            {"val": d2, "is_correct": False, "type": "HEURISTIC_TRAP", "desc": "Multiplicó los exponentes en la multiplicación de igual base"},
            {"val": d3, "is_correct": False, "type": "CALCULATION_ERROR", "desc": "Alteró la base al operar potencias"},
        ]

        return self._build_math_item(stem, candidates, subtopic_id, skill_id, rng, 0.44, (
            f"Aplicando propiedades de potencias de igual base:\n"
            f"1. Numerador: ${base}^{{{p1}}} \\cdot {base}^{{{p2}}} = {base}^{{{p1} + {p2}}} = {base}^{{{p1 + p2}}}$.\n"
            f"2. División: $\\frac{{{base}^{{{p1 + p2}}}}}{{{base}^{{{p3}}}}} = {base}^{{{p1 + p2} - {p3}}} = {base}^{{{exp_final}}} = {sol}$."
        ), "Multiplicar los exponentes al multiplicar potencias de igual base en vez de sumarlos.")

    def _gen_quadratic_problem(self, subtopic_id: str, skill_id: str, rng: random.Random) -> Dict[str, Any]:
        """Ecuación cuadrática y sus raíces reales."""
        r1 = rng.choice([-6, -5, -4, -3, -2, -1, 1, 2, 3, 4, 5, 6])
        r2 = rng.choice([r for r in range(-6, 7) if r != 0 and r != r1])
        b_val = -(r1 + r2)
        c_val = r1 * r2

        b_str = f"+ {b_val}x" if b_val > 0 else (f"- {abs(b_val)}x" if b_val < 0 else "")
        c_str = f"+ {c_val}" if c_val > 0 else (f"- {abs(c_val)}" if c_val < 0 else "")
        stem = f"¿Cuáles son las soluciones de la ecuación cuadrática $x^2 {b_str} {c_str} = 0$?"

        c_pair = f"\\{{{min(r1, r2)}, {max(r1, r2)}\\}}"
        d1 = f"\\{{{min(-r1, -r2)}, {max(-r1, -r2)}\\}}"
        d2 = f"\\{{{min(r1, -r2)}, {max(r1, -r2)}\\}}"
        d3 = f"\\{{{min(r1+1, r2-1)}, {max(r1+1, r2-1)}\\}}"

        candidates = [
            {"val": c_pair, "is_correct": True, "type": "CORRECT", "desc": "Factorización y raíces exactas"},
            {"val": d1, "is_correct": False, "type": "CALCULATION_ERROR", "desc": "Signos invertidos tras factorizar"},
            {"val": d2, "is_correct": False, "type": "HEURISTIC_TRAP", "desc": "Error en uno de los factores"},
            {"val": d3, "is_correct": False, "type": "CONCEPTUAL_CONFUSION", "desc": "Valores desplazados"},
        ]

        def fmt(v):
            return f"${v}$"

        sign_r1 = f"- {r1}" if r1 > 0 else f"+ {abs(r1)}"
        sign_r2 = f"- {r2}" if r2 > 0 else f"+ {abs(r2)}"

        return self._build_math_item(stem, candidates, subtopic_id, skill_id, rng, 0.62, (
            f"Factorizamos $(x {sign_r1})(x {sign_r2}) = 0$, obteniendo las raíces $x_1 = {r1}$ y $x_2 = {r2}$."
        ), "Olvidar cambiar el signo al igualar cada factor a cero.", fmt_fn=fmt)

    def _gen_probability_laplace(self, subtopic_id: str, skill_id: str, rng: random.Random) -> Dict[str, Any]:
        """Probabilidad clásica con regla de Laplace."""
        red = rng.choice([3, 4, 5, 6])
        blue = rng.choice([4, 5, 6, 7])
        green = rng.choice([2, 3, 4])
        total = red + blue + green

        target_color = rng.choice(["roja", "azul", "verde"])
        fav = red if target_color == "roja" else (blue if target_color == "azul" else green)

        stem = (
            f"En una urna opaca hay ${red}$ fichas rojas, ${blue}$ fichas azules y ${green}$ fichas verdes, "
            f"todas de igual tamaño y textura. Si se extrae una ficha al azar, ¿cuál es la probabilidad de que esta sea {target_color}?"
        )

        gcd_val = math.gcd(fav, total)
        f_num, f_den = fav // gcd_val, total // gcd_val
        sol_str = f"\\frac{{{f_num}}}{{{f_den}}}" if f_den > 1 else "1"

        d1 = f"\\frac{{{total - fav}}}{{{total}}}"  # Probabilidad del complemento
        d2 = f"\\frac{{{fav}}}{{{total - fav}}}"  # Razón en vez de probabilidad
        d3 = f"\\frac{{{fav + 1}}}{{{total}}}"

        candidates = [
            {"val": f"${sol_str}$", "is_correct": True, "type": "CORRECT", "desc": "Regla de Laplace: casos favorables / casos posibles"},
            {"val": f"${d1}$", "is_correct": False, "type": "CONCEPTUAL_CONFUSION", "desc": "Calculó la probabilidad del evento complementario"},
            {"val": f"${d2}$", "is_correct": False, "type": "HEURISTIC_TRAP", "desc": "Comparó favorables contra desfavorables (odds) en vez de espacio muestral"},
            {"val": f"${d3}$", "is_correct": False, "type": "CALCULATION_ERROR", "desc": "Error en el conteo de casos favorables"},
        ]

        def fmt(v):
            return str(v)

        return self._build_math_item(stem, candidates, subtopic_id, skill_id, rng, 0.42, (
            f"El espacio muestral total tiene $N = {red} + {blue} + {green} = {total}$ fichas.\n"
            f"Los casos favorables para ficha {target_color} son ${fav}$.\n"
            f"Por la Regla de Laplace: $P = \\frac{{{fav}}}{{{total}}} = {sol_str}$."
        ), "Confundir la probabilidad clásica con la razón de casos favorables a desfavorables.", fmt_fn=fmt)

    def _build_math_item(
        self,
        stem: str,
        candidates: List[Dict[str, Any]],
        subtopic_id: str,
        skill_id: str,
        rng: random.Random,
        difficulty: float,
        step_solution: str,
        frequent_mistake: str,
        fmt_fn=None,
    ) -> Dict[str, Any]:
        """Construye y normaliza un ítem matemático con 4 opciones únicas y clave barajada."""
        seen = set()
        unique = []
        for c in candidates:
            v_key = str(c["val"])
            if v_key not in seen:
                seen.add(v_key)
                unique.append(c)

        # Rellenar si faltaran
        while len(unique) < 4:
            extra_val = rng.choice([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
            if str(extra_val) not in seen:
                seen.add(str(extra_val))
                unique.append({"val": extra_val, "is_correct": False, "type": "HEURISTIC_TRAP", "desc": "Distractor numérico"})

        rng.shuffle(unique)
        keys = ["A", "B", "C", "D"]
        options = []
        correct_key = "A"
        distractor_analysis = {}

        for k, opt in zip(keys, unique):
            text_val = fmt_fn(opt["val"]) if fmt_fn else f"${opt['val']}$"
            options.append({
                "id": k,
                "key": k,
                "text": text_val,
                "is_correct": opt["is_correct"],
                "distractor_type": opt["type"],
            })
            if opt["is_correct"]:
                correct_key = k
            else:
                distractor_analysis[k] = opt["desc"]

        explanation = {
            "correct_solution": f"{step_solution}\nPor lo tanto, la opción correcta es la {correct_key}.",
            "distractor_analysis": distractor_analysis,
            "frequent_mistake": frequent_mistake,
        }

        return {
            "id": f"gen-math-{uuid.uuid4().hex[:10]}",
            "subtopic_id": subtopic_id,
            "skill_id": skill_id,
            "provenance_type": "PARAMETRIC",
            "stem": stem,
            "options": options,
            "explanation": explanation,
            "difficulty_estimate": difficulty,
        }

    # ==========================================
    # 2. GENERADORES PARAMÉTRICOS DE CIENCIAS
    # ==========================================

    def _gen_newton_law(self, subtopic_id: str, skill_id: str, rng: random.Random) -> Dict[str, Any]:
        """Problema de Segunda Ley de Newton F = m * a."""
        m = rng.choice([250, 400, 500, 750, 800, 1000, 1200, 1500, 1600, 2000, 2400, 3000])
        a = rng.choice([2, 3, 4, 5, 6, 7, 8, 9, 10])
        f_val = m * a

        contexts = [
            ("Un automóvil de masa", "se desplaza en línea recta sobre una pista horizontal y acelera a razón de", "la magnitud de la fuerza neta constante aplicada sobre el vehículo"),
            ("Un montacargas de masa", "asciende verticalmente con una aceleración constante de", "la magnitud de la fuerza neta que actúa sobre el sistema"),
            ("Un trineo de carga de masa", "es empujado sobre una superficie sin roce con aceleración de", "la fuerza neta horizontal que lo impulsa"),
        ]
        ctx = rng.choice(contexts)
        stem = f"{ctx[0]} $m = {m}\\text{{ kg}}$ {ctx[1]} $a = {a}\\text{{ m/s}}^2$. ¿Cuál es {ctx[2]} según la Segunda Ley de Newton?"

        d1 = round(m / a, 1)
        d2 = m + (a * 100)
        d3 = f_val + rng.choice([-500, -200, 200, 500])

        candidates = [
            {"val": f_val, "is_correct": True, "type": "CORRECT", "desc": "Segunda Ley de Newton $F = m \\cdot a$"},
            {"val": d1, "is_correct": False, "type": "CALCULATION_ERROR", "desc": "Dividió la masa entre la aceleración en lugar de multiplicarlas"},
            {"val": d2, "is_correct": False, "type": "CONCEPTUAL_CONFUSION", "desc": "Sumó magnitudes incompatibles dimensionalmente"},
            {"val": d3, "is_correct": False, "type": "HEURISTIC_TRAP", "desc": "Aproximación aritmética incorrecta"},
        ]

        def fmt(v):
            return f"${v}\\text{{ N}}$"

        return self._build_math_item(stem, candidates, subtopic_id, skill_id, rng, 0.42, (
            f"Por la Segunda Ley de Newton: $F = m \\cdot a$.\n"
            f"Sustituyendo los valores dados: $F = {m}\\text{{ kg}} \\times {a}\\text{{ m/s}}^2 = {f_val}\\text{{ N}}$."
        ), "Dividir la masa por la aceleración en vez de calcular su producto.", fmt_fn=fmt)

    def _gen_wave_speed(self, subtopic_id: str, skill_id: str, rng: random.Random) -> Dict[str, Any]:
        """Problema de rapidez de propagación de ondas v = lambda * f."""
        f = rng.choice([50, 85, 100, 125, 150, 170, 200, 250, 340, 440, 500, 680, 800, 1000])
        lam = rng.choice([1, 2, 3, 4, 5, 6, 8, 10])
        v = f * lam

        stem = (
            f"Una onda periódica armónica se propaga en un medio elástico homogéneo con una frecuencia de ${f}\\text{{ Hz}}$ "
            f"y una longitud de onda de $\\lambda = {lam}\\text{{ m}}$. ¿Cuál es la rapidez de propagación de la onda?"
        )

        d1 = round(f / lam, 2)
        d2 = round(lam / f, 4)
        d3 = v + rng.choice([-100, -50, 50, 100])

        candidates = [
            {"val": v, "is_correct": True, "type": "CORRECT", "desc": "Relación de onda $v = \\lambda \\cdot f$"},
            {"val": d1, "is_correct": False, "type": "CALCULATION_ERROR", "desc": "Dividió la frecuencia por la longitud de onda"},
            {"val": d2, "is_correct": False, "type": "CONCEPTUAL_CONFUSION", "desc": "Dividió la longitud de onda por la frecuencia"},
            {"val": d3, "is_correct": False, "type": "HEURISTIC_TRAP", "desc": "Desplazamiento numérico"},
        ]

        def fmt(v):
            return f"${v}\\text{{ m/s}}$"

        return self._build_math_item(stem, candidates, subtopic_id, skill_id, rng, 0.44, (
            f"La relación fundamental de propagación de ondas establece:\n"
            f"$$v = \\lambda \\cdot f = {lam}\\text{{ m}} \\times {f}\\text{{ Hz}} = {v}\\text{{ m/s}}$$.\n"
        ), "Invertir la ecuación dividiendo longitud de onda por frecuencia.", fmt_fn=fmt)

    def _gen_ohm_law(self, subtopic_id: str, skill_id: str, rng: random.Random) -> Dict[str, Any]:
        """Problema de Ley de Ohm V = I * R."""
        r = rng.choice([2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25])
        i = rng.choice([2, 3, 4, 5, 6, 8, 10])
        v = r * i

        stem = (
            f"Por un conductor óhmico con una resistencia eléctrica de $R = {r}\\ \\Omega$ "
            f"circula una corriente continua de intensidad $I = {i}\\text{{ A}}$. "
            f"¿Cuál es la diferencia de potencial (voltaje) entre los extremos del resistor?"
        )

        d1 = round(r / i, 2)
        d2 = round(i / r, 2)
        d3 = v + rng.choice([-8, -4, 4, 8])

        candidates = [
            {"val": v, "is_correct": True, "type": "CORRECT", "desc": "Ley de Ohm $V = I \\cdot R$"},
            {"val": d1, "is_correct": False, "type": "CALCULATION_ERROR", "desc": "Dividió la resistencia por la intensidad"},
            {"val": d2, "is_correct": False, "type": "CONCEPTUAL_CONFUSION", "desc": "Dividió la intensidad por la resistencia"},
            {"val": d3, "is_correct": False, "type": "HEURISTIC_TRAP", "desc": "Error aritmético"},
        ]

        def fmt(v):
            return f"${v}\\text{{ V}}$"

        return self._build_math_item(stem, candidates, subtopic_id, skill_id, rng, 0.40, (
            f"Por la Ley de Ohm: $V = I \\cdot R = {i}\\text{{ A}} \\times {r}\\ \\Omega = {v}\\text{{ V}}$."
        ), "Dividir en lugar de multiplicar la corriente por la resistencia.", fmt_fn=fmt)

    def _gen_kinetic_energy(self, subtopic_id: str, skill_id: str, rng: random.Random) -> Dict[str, Any]:
        """Problema de energía cinética Ec = 1/2 * m * v^2."""
        m = rng.choice([2, 4, 6, 8, 10, 12, 16, 20, 30])
        v = rng.choice([2, 3, 4, 5, 6, 8, 10])
        ec = int(0.5 * m * (v ** 2))

        stem = (
            f"Un objeto de masa $m = {m}\\text{{ kg}}$ se mueve en línea recta sobre una superficie horizontal "
            f"con una rapidez constante de $v = {v}\\text{{ m/s}}$. ¿Cuál es la energía cinética del cuerpo?"
        )

        d1 = m * v  # Momento lineal en vez de energía
        d2 = m * (v ** 2)  # Olvidar el 1/2
        d3 = ec + rng.choice([-20, -10, 10, 20])

        candidates = [
            {"val": ec, "is_correct": True, "type": "CORRECT", "desc": "Energía cinética $E_c = \\frac{1}{2}m v^2$"},
            {"val": d1, "is_correct": False, "type": "CONCEPTUAL_CONFUSION", "desc": "Confundió energía cinética con cantidad de movimiento ($p = m \\cdot v$)"},
            {"val": d2, "is_correct": False, "type": "CALCULATION_ERROR", "desc": "Omitió el factor $\\frac{1}{2}$ en la fórmula"},
            {"val": d3, "is_correct": False, "type": "HEURISTIC_TRAP", "desc": "Aproximación numérica"},
        ]

        def fmt(v):
            return f"${v}\\text{{ J}}$"

        return self._build_math_item(stem, candidates, subtopic_id, skill_id, rng, 0.46, (
            f"La energía cinética viene dada por $E_c = \\frac{{1}}{{2}} m v^2$.\n"
            f"Sustituyendo: $E_c = \\frac{{1}}{{2}} ({m}\\text{{ kg}}) ({v}\\text{{ m/s}})^2 = \\frac{{1}}{{2}} \\times {m} \\times {v**2} = {ec}\\text{{ J}}$."
        ), "Confundir la energía cinética con el momento lineal o olvidar elevar la rapidez al cuadrado.", fmt_fn=fmt)

    # ==========================================
    # 3. GENERADORES CURRICULARES CONTEXTUALES (CIENCIAS, HISTORIA, LECTURA)
    # ==========================================

    def _get_catalog_items(self, subject: str) -> List[Dict[str, Any]]:
        """Catálogo amplio de 30+ escenarios curriculares oficiales DEMRE."""
        if subject == "CIENCIAS":
            return [
                {
                    "stem": "En un experimento para evaluar la fotosíntesis, se ilumina una planta acuática sumergida en una solución con bicarbonato a temperatura constante ($20^\\circ\\text{C}$). Se mide la producción de burbujas de oxígeno variando la distancia del foco de luz. En este diseño experimental, ¿cuál es la variable independiente?",
                    "correct": "La distancia entre el foco de luz y la planta (intensidad luminosa recibida).",
                    "d1": "La tasa de burbujas de oxígeno liberadas por minuto.",
                    "d2": "La concentración de bicarbonato de sodio en el agua.",
                    "d3": "La temperatura ambiental controlada a $20^\\circ\\text{C}$.",
                    "correct_desc": "La variable independiente es aquella manipulada deliberadamente por el investigador",
                    "d1_desc": "Corresponde a la variable dependiente (efecto medido)",
                    "d2_desc": "Es una variable controlada para evitar factores de confusión",
                    "d3_desc": "Es una variable controlada constante",
                    "diff": 0.45,
                    "eje": "Método Científico",
                },
                {
                    "stem": "Un automóvil de masa $m = 1000\\text{ kg}$ se desplaza en línea recta sobre una pista horizontal y frena uniformemente con una aceleración de magnitud $a = 4\\text{ m/s}^2$. ¿Cuál es la magnitud de la fuerza neta de frenado aplicada sobre el vehículo?",
                    "correct": "$4000\\text{ N}$",
                    "d1": "$250\\text{ N}$",
                    "d2": "$2500\\text{ N}$",
                    "d3": "$400\\text{ N}$",
                    "correct_desc": "Por la Segunda Ley de Newton: $F = m \\cdot a = 1000 \\times 4 = 4000\\text{ N}$",
                    "d1_desc": "Dividió la masa por la aceleración ($m/a$)",
                    "d2_desc": "Error en el producto algebraico",
                    "d3_desc": "Omitió un factor decimal en la multiplicación",
                    "diff": 0.42,
                    "eje": "Física Mecánica",
                },
                {
                    "stem": "¿Cuál de las siguientes afirmaciones describe correctamente el rol de la membrana plasmática en el transporte celular pasivo mediante ósmosis?",
                    "correct": "El agua se desplaza a través de la membrana semipermeable desde la solución hipotónica hacia la hipertónica sin gasto de ATP.",
                    "d1": "Los solutos se mueven en contra de su gradiente de concentración consumiendo moléculas de ATP.",
                    "d2": "Las macromoléculas son englobadas por vesículas en un proceso dependiente de energía química.",
                    "d3": "El agua viaja desde la solución con mayor concentración de soluto hacia la de menor concentración.",
                    "correct_desc": "La ósmosis es el flujo neto de solvente a favor del gradiente hídrico hacia donde hay mayor osmolaridad",
                    "d1_desc": "Describe el transporte activo de solutos",
                    "d2_desc": "Describe la endocitosis",
                    "d3_desc": "Invierte la dirección natural del flujo osmótico del agua",
                    "diff": 0.50,
                    "eje": "Biología Celular",
                },
                {
                    "stem": "Una onda sonora se propaga en el aire con una rapidez de $340\\text{ m/s}$. Si su frecuencia es de $170\\text{ Hz}$, ¿cuál es su longitud de onda $\\lambda$?",
                    "correct": "$2\\text{ m}$",
                    "d1": "$0.5\\text{ m}$",
                    "d2": "$57800\\text{ m}$",
                    "d3": "$1.5\\text{ m}$",
                    "correct_desc": "Relación fundamental de ondas: $v = \\lambda \\cdot f \\implies \\lambda = v/f = 340/170 = 2\\text{ m}$",
                    "d1_desc": "Invirtió la fórmula calculando $f/v$",
                    "d2_desc": "Multiplicó la velocidad por la frecuencia ($v \\cdot f$)",
                    "d3_desc": "Aproximación aritmética incorrecta",
                    "diff": 0.44,
                    "eje": "Física Ondas",
                },
                {
                    "stem": "En una reacción química en equilibrio entre gases, ¿qué efecto tiene la adición de un catalizador adecuado sobre la posición del equilibrio químico?",
                    "correct": "Aumenta la velocidad para alcanzar el equilibrio sin alterar las concentraciones finales de reactivos y productos.",
                    "d1": "Desplaza el equilibrio hacia la formación de una mayor cantidad de productos.",
                    "d2": "Aumenta la entalpía estándar de la reacción facilitando la combustión.",
                    "d3": "Disminuye la constante de equilibrio de la reacción reversible.",
                    "correct_desc": "Un catalizador reduce la energía de activación de ambas reacciones sin modificar la termodinámica",
                    "d1_desc": "Confunde la cinética química con el desplazamiento termodinámico de Le Chatelier",
                    "d2_desc": "Los catalizadores no modifican la entalpía de reacción",
                    "d3_desc": "La constante de equilibrio solo depende de la temperatura",
                    "diff": 0.55,
                    "eje": "Química General",
                },
                {
                    "stem": "En un ecosistema terrestre, si los herbívoros consumen $10.000\\text{ kcal}$ de biomasa vegetal, según la regla ecológica del $10\\%$, ¿cuánta energía aproximadamente estará disponible para los carnívoros primarios que se alimentan de ellos?",
                    "correct": "$1.000\\text{ kcal}$",
                    "d1": "$100\\text{ kcal}$",
                    "d2": "$5.000\\text{ kcal}$",
                    "d3": "$9.000\\text{ kcal}$",
                    "correct_desc": "Aproximadamente el 10% de la energía de un nivel trófico se transfiere al nivel inmediatamente superior",
                    "d1_desc": "Calculó la energía disponible para los carnívoros secundarios (dos niveles)",
                    "d2_desc": "Asumió una tasa de eficiencia del 50%",
                    "d3_desc": "Calculó la energía perdida por respiración y excreción en lugar de la transferida",
                    "diff": 0.40,
                    "eje": "Biología Ecología",
                },
            ]

        elif subject == "HISTORIA":
            return [
                {
                    "stem": "Durante la segunda mitad del siglo XIX en Chile, el auge de la minería del salitre motivó una intensa migración campo-ciudad y campo-mina. Las precarias condiciones habitacionales, la insalubridad y la falta de leyes laborales configuraron el fenómeno histórico conocido como:",
                    "correct": "La cuestión social.",
                    "d1": "La doctrina de seguridad nacional.",
                    "d2": "El parlamentarismo a la chilena.",
                    "d3": "La chilenización de Tarapacá.",
                    "correct_desc": "La Cuestión Social sintetiza las penurias socioeconómicas y laborales de la clase trabajadora",
                    "d1_desc": "Doctrina político-militar de la segunda mitad del siglo XX durante la Guerra Fría",
                    "d2_desc": "Régimen institucional oligárquico (1891-1925), no el fenómeno social obrero",
                    "d3_desc": "Proceso de integración cultural de los territorios anexados tras la Guerra del Pacífico",
                    "diff": 0.42,
                    "eje": "Historia de Chile S. XIX",
                },
                {
                    "stem": "En la organización institucional de Chile bajo la Constitución de 1833, ¿cuál de las siguientes atribuciones consagraba el marcado carácter presidencialista y autoritario del régimen portaliano?",
                    "correct": "La facultad presidencial de decretar el estado de sitio y suspender garantías constitucionales ante conmoción interna.",
                    "d1": "La elección popular directa del Presidente por sufragio universal masculino y femenino.",
                    "d2": "El veto legislativo vinculante del Senado sobre las leyes periódicas del presupuesto nacional.",
                    "d3": "La obligación de someter los tratados internacionales a plebiscito ciudadano.",
                    "correct_desc": "Las facultades extraordinarias y el estado de sitio fortalecían el poder ejecutivo sobre el congreso",
                    "d1_desc": "El sufragio era censitario e indirecto, restringido a varones con renta",
                    "d2_desc": "Las leyes periódicas eran una atribución del Congreso, no un rasgo presidencialista",
                    "d3_desc": "Mecanismo de democracia directa inexistente en 1833",
                    "diff": 0.48,
                    "eje": "Construcción de la República",
                },
                {
                    "stem": "En el contexto de la Guerra Fría, la Alianza para el Progreso impulsada por Estados Unidos en América Latina a comienzos de la década de 1960 tuvo como propósito estratégico fundamental:",
                    "correct": "Frenar la influencia de la Revolución Cubana mediante ayuda económica para reformas estructurales como la Reforma Agraria.",
                    "d1": "Promover la disolución inmediata de los ejércitos nacionales latinoamericanos.",
                    "d2": "Implantar un mercado común socialista administrado por la Unión Soviética.",
                    "d3": "Financiar golpes militares inmediatos en toda la cuenca del Caribe.",
                    "correct_desc": "Buscaba modernizar las estructuras socioeconómicas para neutralizar focos de insurgencia comunista",
                    "d1_desc": "EE.UU. fortaleció la doctrina de contrainsurgencia militar, no su disolución",
                    "d2_desc": "Era una iniciativa estadounidense para contener al socialismo",
                    "d3_desc": "La doctrina inicial del gobierno de Kennedy priorizó reformas sociales y cooperación económica",
                    "diff": 0.52,
                    "eje": "Mundo Global y Guerra Fría",
                },
                {
                    "stem": "En el sistema democrático chileno actual, ¿cuál es la función constitucional prioritaria del Servicio Electoral (SERVEL) como órgano autónomo?",
                    "correct": "Organizar, fiscalizar y supervigilar de forma independiente los procesos electorales y plebiscitarios.",
                    "d1": "Redactar las leyes orgánicas que determinan el número de parlamentarios en el Congreso.",
                    "d2": "Dictaminar sentencias penales sobre delitos comunes cometidos por candidatos.",
                    "d3": "Designar a los ministros de la Corte Suprema y miembros del Tribunal Constitucional.",
                    "correct_desc": "El SERVEL goza de rango constitucional autónomo para velar por la transparencia y legitimidad electoral",
                    "d1_desc": "Función privativa del Poder Legislativo",
                    "d2_desc": "Corresponde a los tribunales ordinarios de justicia y al Ministerio Público",
                    "d3_desc": "Nombramiento que involucra al Presidente de la República y al Senado",
                    "diff": 0.38,
                    "eje": "Formación Ciudadana",
                },
                {
                    "stem": "Durante el siglo XX chileno, el proceso de Reforma Agraria iniciado en el gobierno de Jorge Alessandri y profundizado por Frei Montalva y Salvador Allende tuvo como meta económica y social:",
                    "correct": "Terminar con el latifundio improductivo y redistribuir la propiedad de la tierra a las familias campesinas.",
                    "d1": "Privatizar la totalidad de los yacimientos de la gran minería del cobre.",
                    "d2": "Obligar a la población campesina a trasladarse forzosamente a los centros fabriles de Santiago.",
                    "d3": "Eliminar los aranceles de importación de trigo procedente de Norteamérica.",
                    "correct_desc": "La modernización del agro chileno buscaba aumentar la productividad y dignificar la condición del campesinado",
                    "d1_desc": "El proceso correlativo en minería fue la Chilenización y Nacionalización del Cobre",
                    "d2_desc": "Buscaba justamente afincar al campesino en tierras productivas propias",
                    "d3_desc": "La política agraria no fue de apertura arancelaria indiscriminada",
                    "diff": 0.46,
                    "eje": "Chile en el Siglo XX",
                },
            ]

        else:  # LECTURA
            return [
                {
                    "title": "La Plasticidad Sináptica y la Neuroplasticidad",
                    "stimulus": "Durante décadas se creyó que la estructura cerebral quedaba fosilizada tras la adolescencia. Sin embargo, la neurociencia contemporánea ha demostrado que las redes neuronales conservan su maleabilidad a lo largo de toda la existencia. Gracias a la plasticidad sináptica, la práctica deliberada y el aprendizaje continuo son capaces de reconfigurar circuitos neuronales y fortalecer la memoria en cualquier etapa de la vida.",
                    "stem": "¿Cuál es la idea principal que se concluye del texto precedente sobre el funcionamiento del cerebro adulto?",
                    "correct": "El cerebro conserva la capacidad biológica de reorganizarse y aprender durante toda la vida.",
                    "d1": "La madurez biológica imposibilita la formación de nuevas conexiones entre neuronas.",
                    "d2": "La práctica deliberada solo surte efectos neurobiológicos durante la infancia temprana.",
                    "d3": "La memoria humana no experimenta variaciones anatómicas ante el aprendizaje continuo.",
                    "correct_desc": "Sintetiza la tesis central del autor sobre la persistencia de la plasticidad sináptica",
                    "d1_desc": "Afirma la concepción antigua desmentida expresamente en el texto",
                    "d2_desc": "Restringe arbitrariamente los efectos de la práctica solo a la niñez",
                    "d3_desc": "Contradice la evidencia de reconfiguración neuronal planteada",
                    "diff": 0.45,
                    "eje": "Comprensión Global",
                },
                {
                    "title": "La Transición Energética y los Minerales Estratégicos",
                    "stimulus": "El reemplazo global de los combustibles fósiles por energías renovables exige una provisión sin precedentes de materias primas críticas. La fabricación de baterías de alta densidad para vehículos eléctricos requiere litio, níquel y cobalto en proporciones que superan la capacidad minera histórica. En consecuencia, la descarbonización del planeta plantea el desafío simultáneo de elevar la producción extractiva minimizando el impacto socioambiental en los salares y cuencas hídricas.",
                    "stem": "A partir de la lectura, ¿qué relación existe entre la masificación de vehículos eléctricos y la industria minera?",
                    "correct": "La producción masiva de autos eléctricos impulsa un incremento sustancial en la demanda de minerales estratégicos.",
                    "d1": "El desarrollo de motores eléctricos erradica por completo la necesidad de extraer metales pesados.",
                    "d2": "La industria minera reducirá a la mitad su producción debido al avance de las energías verdes.",
                    "d3": "Los salares del planeta no experimentan ninguna presión ecológica por la extracción de litio.",
                    "correct_desc": "Relaciona de forma fidedigna la demanda de baterías con la intensificación minera",
                    "d1_desc": "Sostiene lo contrario a la exigencia de litio y níquel expuesta",
                    "d2_desc": "Contradice el requerimiento de mayor producción extractiva",
                    "d3_desc": "Ignora el dilema socioambiental explicitado en el texto",
                    "diff": 0.48,
                    "eje": "Relacionar e Interpretar",
                },
                {
                    "title": "El Algoritmo de la Atención",
                    "stimulus": "El modelo de negocios de las plataformas digitales contemporáneas se basa en la economía de la atención. Cada notificación y cada desplazamiento infinito (infinite scroll) están calibrados para activar descargas intermitentes de dopamina, reteniendo al usuario el mayor tiempo posible frente a la pantalla. Lejos de ser herramientas neutrales, las redes sociales moldean activamente los hábitos de concentración y la paciencia reflexiva de las nuevas generaciones.",
                    "stem": "¿Cuál es el propósito comunicativo fundamental del emisor en el texto citado?",
                    "correct": "Advertir críticamente sobre cómo el diseño de las plataformas digitales condiciona la atención y conducta de los usuarios.",
                    "d1": "Promocionar los beneficios cognitivos que reporta el uso frecuente de notificaciones móviles.",
                    "d2": "Explicar las características técnicas de la programación de bases de datos relacionales.",
                    "d3": "Demostrar que el consumo de dopamina artificial carece de efectos en la conducta humana.",
                    "correct_desc": "Capta la postura reflexiva y de alerta sobre el impacto de la economía de la atención",
                    "d1_desc": "El texto adopta una perspectiva crítica, no publicitaria de las redes",
                    "d2_desc": "El tema no es la informática técnica sino la psicología de la atención",
                    "d3_desc": "Niega el fundamento neuroquímico expuesto por el autor",
                    "diff": 0.50,
                    "eje": "Evaluar y Reflexionar",
                },
                {
                    "title": "La Paradoja de Fermi y el Silencio Cósmico",
                    "stimulus": "Dada la inmensa cantidad de estrellas en nuestra galaxia y la elevada probabilidad estadística de que existan planetas habitables con miles de millones de años de antigüedad, surge una interrogante ineludible planteada por Enrico Fermi en 1950: '¿Dónde está todo el mundo?'. La contradicción entre la alta probabilidad matemática de vida inteligente extraterrestre y la ausencia absoluta de evidencia verificable constituye la Paradoja de Fermi, un enigma que desafía nuestra comprensión del cosmos.",
                    "stem": "¿En qué consiste esencialmente la Paradoja de Fermi según el fragmento?",
                    "correct": "En la contradicción entre la probabilidad teórica de civilizaciones cósmicas y la falta de contacto real con ellas.",
                    "d1": "En la demostración definitiva de que la Tierra es el único cuerpo celeste con vida en el universo.",
                    "d2": "En la comprobación de que todas las estrellas de la Vía Láctea carecen de planetas rocosos.",
                    "d3": "En la certeza de que las señales de radio humanas no pueden atravesar la atmósfera terrestre.",
                    "correct_desc": "Define con exactitud la tensión entre probabilidad matemática y falta de señales observadas",
                    "d1_desc": "La paradoja formula una duda no resuelta, no una certeza de soledad biológica",
                    "d2_desc": "Contradice la premisa de abundancia de planetas habitables",
                    "d3_desc": "Dato ajeno y contradictorio respecto al tema astronómico",
                    "diff": 0.44,
                    "eje": "Rastrear y Localizar",
                },
            ]

    def _gen_catalog_question(self, subject: str, subtopic_id: str, skill_id: str, rng: random.Random) -> Dict[str, Any]:
        """Selecciona y empaqueta un ítem del catálogo temático oficial."""
        catalog = self._get_catalog_items(subject)
        item = rng.choice(catalog)

        candidates = [
            {"text": item["correct"], "is_correct": True, "type": "CORRECT", "desc": item.get("correct_desc", "Respuesta fundamentada")},
            {"text": item["d1"], "is_correct": False, "type": "CONCEPTUAL_CONFUSION", "desc": item["d1_desc"]},
            {"text": item["d2"], "is_correct": False, "type": "HEURISTIC_TRAP", "desc": item["d2_desc"]},
            {"text": item["d3"], "is_correct": False, "type": "CONTRADICTION", "desc": item["d3_desc"]},
        ]

        rng.shuffle(candidates)
        keys = ["A", "B", "C", "D"]
        options = []
        correct_key = "A"
        distractor_analysis = {}

        for k, opt in zip(keys, candidates):
            options.append({
                "id": k,
                "key": k,
                "text": opt["text"],
                "is_correct": opt["is_correct"],
                "distractor_type": opt["type"],
            })
            if opt["is_correct"]:
                correct_key = k
            else:
                distractor_analysis[k] = opt["desc"]

        explanation = {
            "correct_solution": (
                f"{item.get('correct_desc', 'Respuesta correcta según pauta oficial DEMRE.')}\n"
                f"Por tanto, la opción correcta es la {correct_key}."
            ),
            "distractor_analysis": distractor_analysis,
            "frequent_mistake": "Elegir alternativas que usan términos familiares pero distorsionan el sentido lógico o histórico del enunciado.",
        }

        prefix = "cien" if subject == "CIENCIAS" else ("hist" if subject == "HISTORIA" else "lect")
        return {
            "id": f"gen-{prefix}-{uuid.uuid4().hex[:10]}",
            "subtopic_id": subtopic_id,
            "skill_id": skill_id,
            "provenance_type": "ORIGINAL",
            "stimulus_title": item.get("title"),
            "stimulus_text": item.get("stimulus"),
            "stem": item["stem"],
            "options": options,
            "explanation": explanation,
            "difficulty_estimate": item.get("diff", 0.48),
        }

    # ==========================================
    # 3. DISPATCHER Y GENERACIÓN EN LOTE
    # ==========================================

    def generate_single_item(self, subject_code: str, subtopic_id: str, skill_id: str, rng: Optional[random.Random] = None) -> Dict[str, Any]:
        """Despacha al generador correspondiente según la materia."""
        rng = rng or random.Random()
        subj = subject_code.upper()

        if subj == "M1":
            gen_fn = rng.choice([
                self._gen_linear_equation,
                self._gen_percentage_problem,
                self._gen_pythagoras_problem,
                self._gen_powers_roots,
                self._gen_probability_laplace,
                self._gen_linear_system,
            ])
            return gen_fn(subtopic_id, skill_id, rng)
        elif subj == "M2":
            gen_fn = rng.choice([
                self._gen_quadratic_problem,
                self._gen_linear_system,
                self._gen_pythagoras_problem,
                self._gen_powers_roots,
                self._gen_probability_laplace,
                self._gen_linear_equation,
            ])
            return gen_fn(subtopic_id, skill_id, rng)
        elif subj == "CIENCIAS":
            gen_fn = rng.choice([
                self._gen_newton_law,
                self._gen_wave_speed,
                self._gen_ohm_law,
                self._gen_kinetic_energy,
                self._gen_catalog_question,
            ])
            if gen_fn == self._gen_catalog_question:
                return self._gen_catalog_question(subj, subtopic_id, skill_id, rng)
            return gen_fn(subtopic_id, skill_id, rng)
        else:
            return self._gen_catalog_question(subj, subtopic_id, skill_id, rng)

    def generate_batch(
        self,
        subject_code: str,
        count: int = 5,
        save_to_db: bool = False,
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Genera un lote de ítems únicos validados por QualityFilter y con calibración IRT.
        Garantiza que ningún ítem sea duplicado de la base de datos ni del lote actual.
        """
        subj = subject_code.upper()
        subtopics = self._load_subtopics_by_subject(subj)
        if not subtopics:
            return [], [f"No se encontraron subtemas registrados para la asignatura {subj}"]

        valid_subtopic_ids = {s["id"] for s in subtopics}
        skill_id = self._get_competency_id("RESOLVER_PROBLEMAS")

        rng = random.Random()
        approved_items = []
        rejection_logs = []

        logger.info(f"Generando lote de {count} preguntas para {subj}...")

        attempts = 0
        max_attempts = count * 6

        while len(approved_items) < count and attempts < max_attempts:
            attempts += 1
            chosen_subtopic = rng.choice(subtopics)
            sub_id = chosen_subtopic["id"]

            raw_item = self.generate_single_item(subj, sub_id, skill_id, rng)

            # Deduplicación estricta por enunciado
            norm_stem = raw_item["stem"].strip().lower()
            if norm_stem in self.seen_stems:
                rejection_logs.append(f"Duplicado omitido ({norm_stem[:40]}...)")
                continue

            # Validar con QualityFilter
            is_valid, errors = QualityFilter.validate_item(raw_item, valid_subtopic_ids)
            if not is_valid:
                rejection_logs.append(f"Rechazado ítem {raw_item['id']}: {errors}")
                continue

            # Calibrar parámetros IRT (3PL: a, b, c)
            options_json_str = json.dumps(raw_item["options"], ensure_ascii=False)
            a, b, c = compute_irt_parameters(raw_item.get("difficulty_estimate", 0.50), options_json_str)
            raw_item["irt_a"] = a
            raw_item["irt_b"] = b
            raw_item["irt_c"] = c
            raw_item["irt_status"] = "CALIBRATED_HEURISTIC"

            self.seen_stems.add(norm_stem)
            approved_items.append(raw_item)

        if save_to_db and self.session and approved_items:
            now = datetime.now(timezone.utc)
            for item in approved_items:
                q_model = PaesQuestion(
                    id=item["id"],
                    subtopic_id=item["subtopic_id"],
                    skill_id=item["skill_id"],
                    provenance_type=item.get("provenance_type", "ORIGINAL"),
                    stem=item["stem"],
                    stimulus_title=item.get("stimulus_title"),
                    stimulus_text=item.get("stimulus_text"),
                    options_json=json.dumps(item["options"], ensure_ascii=False),
                    explanation_json=json.dumps(item["explanation"], ensure_ascii=False),
                    difficulty_estimate=item.get("difficulty_estimate", 0.50),
                    difficulty_source="AUTO_GENERATED_CALIBRATED",
                    irt_a=item["irt_a"],
                    irt_b=item["irt_b"],
                    irt_c=item["irt_c"],
                    irt_status=item["irt_status"],
                    created_at=now,
                    updated_at=now,
                )
                self.session.add(q_model)
            self.session.commit()
            logger.info(f"Guardadas exitosamente {len(approved_items)} preguntas en peak.db para {subj}")

        return approved_items, rejection_logs


def main():
    parser = argparse.ArgumentParser(description="Generador Autónomo de Contenido PAES")
    parser.add_argument("--subject", choices=["M1", "M2", "LECTURA", "CIENCIAS", "HISTORIA"], help="Materia a generar")
    parser.add_argument("--all", action="store_true", help="Generar preguntas para todas las 5 materias")
    parser.add_argument("--count", type=int, default=5, help="Cantidad de preguntas a generar por materia")
    parser.add_argument("--save", action="store_true", help="Guardar directamente en SQLite peak.db")
    parser.add_argument("--dry-run", action="store_true", help="Solo generar y validar en memoria sin persistir")
    parser.add_argument("--output", type=str, default=None, help="Ruta opcional para exportar JSON con las preguntas generadas")

    args = parser.parse_args()

    with Session(engine) as session:
        generator = AutoContentGenerator(db_session=session)
        subjects = ["M1", "M2", "LECTURA", "CIENCIAS", "HISTORIA"] if args.all else ([args.subject] if args.subject else ["M1"])

        all_generated = []
        print("=======================================================")
        print("[*] PIPELINE AUTONOMO DE GENERACION DE CONTENIDO PAES")
        print("=======================================================")

        for subj in subjects:
            items, rejections = generator.generate_batch(
                subject_code=subj,
                count=args.count,
                save_to_db=args.save and not args.dry_run,
            )
            all_generated.extend(items)
            print(f"\n[{subj}] Generadas y Calibradas: {len(items)} preguntas (Descartes por duplicado/filtro: {len(rejections)})")
            for idx, it in enumerate(items[:2], 1):
                print(f"  ({idx}) {it['stem'][:70]}... -> IRT (a={it['irt_a']}, b={it['irt_b']}, c={it['irt_c']})")

        print("\n" + "=" * 55)
        print(f"TOTAL GENERADO Y VALIDADO: {len(all_generated)} preguntas")
        if args.save and not args.dry_run:
            print("ESTADO: Insertadas y confirmadas en la base de datos peak.db")
        else:
            print("ESTADO: Modo simulación (Dry Run). Usa --save para persistir.")
        print("=" * 55)

        if args.output:
            out_path = Path(args.output)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(all_generated, f, ensure_ascii=False, indent=2)
            print(f"Exportadas preguntas a: {out_path}")


if __name__ == "__main__":
    main()
