"""
Banco Curado de Preguntas de Alta Calidad DEMRE para Peak.
Materias: Competencia Lectora, Matemática 2 (M2), Ciencias (Bio/Fís/Quím), Historia.
Cada ítem cuenta con estímulo, análisis de distractores, KaTeX balanceado y competencias oficiales.
"""

QUALITY_QUESTIONS = [
    # =========================================================================
    # 1. COMPETENCIA LECTORA
    # =========================================================================
    {
        "id": "q-lec-bio-01",
        "subtopic_id": "sub-lec-ia-sociedad",
        "skill_code": "RASTREAR_LOCALIZAR",
        "stimulus_title": "El microbioma humano y el eje intestino-cerebro",
        "stimulus_text": (
            "La microbiota intestinal, compuesta por billones de bacterias que habitan el tracto gastrointestinal, "
            "ha dejado de ser considerada una simple comunidad comensal para ser entendida como un órgano metabólico activo. "
            "A través del eje intestino-cerebro, estas bacterias se comunican de forma bidireccional con el sistema nervioso central.\n\n"
            "Uno de los mecanismos bioquímicos clave es la síntesis de ácidos grasos de cadena corta (AGCC), tales como el butirato, "
            "generados tras la fermentación de fibras dietéticas solubles. El butirato preserva la integridad de la barrera "
            "hematoencefálica, limitando el paso de endotoxinas inflamatorias hacia el cerebro. Asimismo, más del 90% de la serotonina "
            "corporal es sintetizada en las células enterocromafines del epitelio intestinal bajo modulación de metabolitos bacterianos."
        ),
        "stem": "¿Cuál es la función específica del butirato mencionada explícitamente en el segundo párrafo?",
        "options": [
            {"key": "A", "text": "Preservar la integridad de la barrera hematoencefálica y limitar endotoxinas.", "is_correct": True, "distractor_type": "CORRECT"},
            {"key": "B", "text": "Sintetizar directamente la totalidad de la serotonina corporal en el encéfalo.", "is_correct": False, "distractor_type": "CONFUSION_SITE"},
            {"key": "C", "text": "Reemplazar de forma definitiva a los neurotransmisores del sistema nervioso.", "is_correct": False, "distractor_type": "OVERGENERALIZATION"},
            {"key": "D", "text": "Inhibir la fermentación de fibras solubles en el tracto gástrico superior.", "is_correct": False, "distractor_type": "CONTRADICTION"},
        ],
        "explanation": {
            "correct_solution": "El texto explicita textualmente que el butirato 'preserva la integridad de la barrera hematoencefálica, limitando el paso de endotoxinas inflamatorias hacia el cerebro'.",
            "skill_evaluated": "Rastrear - Localizar información explícita."
        },
        "difficulty_estimate": 0.35,
    },
    {
        "id": "q-lec-bio-02",
        "subtopic_id": "sub-lec-ia-sociedad",
        "skill_code": "RELACIONAR_INTERPRETAR",
        "stimulus_title": "El microbioma humano y el eje intestino-cerebro",
        "stimulus_text": (
            "La microbiota intestinal, compuesta por billones de bacterias que habitan el tracto gastrointestinal, "
            "ha dejado de ser considerada una simple comunidad comensal para ser entendida como un órgano metabólico activo. "
            "A través del eje intestino-cerebro, estas bacterias se comunican de forma bidireccional con el sistema nervioso central.\n\n"
            "Uno de los mecanismos bioquímicos clave es la síntesis de ácidos grasos de cadena corta (AGCC), tales como el butirato, "
            "generados tras la fermentación de fibras dietéticas solubles. El butirato preserva la integridad de la barrera "
            "hematoencefálica, limitando el paso de endotoxinas inflamatorias hacia el cerebro. Asimismo, más del 90% de la serotonina "
            "corporal es sintetizada en las células enterocromafines del epitelio intestinal bajo modulación de metabolitos bacterianos."
        ),
        "stem": "A partir de lo expuesto en el fragmento, ¿qué relación se puede inferir entre la alimentación y la salud neurológica?",
        "options": [
            {"key": "A", "text": "El consumo de fibras dietéticas solubles promueve la síntesis de metabolitos neuroprotectores.", "is_correct": True, "distractor_type": "CORRECT"},
            {"key": "B", "text": "La producción de serotonina intestinal hace innecesaria la actividad neuronal del cerebro.", "is_correct": False, "distractor_type": "EXTREME_ABSURD"},
            {"key": "C", "text": "Las endotoxinas son indispensables para la comunicación del eje intestino-cerebro.", "is_correct": False, "distractor_type": "FALSE_CORRELATION"},
            {"key": "D", "text": "La microbiota actúa de manera totalmente independiente de los alimentos ingeridos.", "is_correct": False, "distractor_type": "CONTRADICTION"},
        ],
        "explanation": {
            "correct_solution": "Dado que las fibras solubles son fermentadas para producir AGCC como el butirato, y este protege la barrera hematoencefálica, se infiere una relación directa entre ingesta de fibra y neuroprotección.",
            "skill_evaluated": "Relacionar - Interpretar inferencias a partir del texto."
        },
        "difficulty_estimate": 0.50,
    },
    {
        "id": "q-lec-etica-01",
        "subtopic_id": "sub-lec-columnas-opinion",
        "skill_code": "EVALUAR_REFLEXIONAR",
        "stimulus_title": "La ilusión de la neutralidad algorítmica",
        "stimulus_text": (
            "Se suele afirmar con ligereza que las decisiones automatizadas por modelos de aprendizaje profundo son inherentemente "
            "más justas que el criterio humano porque 'los números no tienen prejuicios'. Nada más alejado de la realidad empírica. "
            "Un algoritmo no desciende del cielo platónico de las matemáticas puras: es entrenado con datos históricos que "
            "sistematizan desigualdades estructurales, sesgos judiciales y disparidades económicas previas. Delegar ciegamente "
            "decisiones penales o de asignación de créditos a una 'caja negra' no elimina el sesgo, solo lo tecnifica y lo blinda "
            "contra la apelación democrática."
        ),
        "stem": "¿Cuál es el propósito comunicativo central del autor en este párrafo?",
        "options": [
            {"key": "A", "text": "Cuestionar la supuesta imparcialidad de los algoritmos demostrando que heredan sesgos humanos históricos.", "is_correct": True, "distractor_type": "CORRECT"},
            {"key": "B", "text": "Proponer la prohibición absoluta de la informática en el sistema judicial y bancario.", "is_correct": False, "distractor_type": "EXTREMISMO"},
            {"key": "C", "text": "Explicar los fundamentos matemáticos que rigen el entrenamiento del aprendizaje profundo.", "is_correct": False, "distractor_type": "MISPLACED_TOPIC"},
            {"key": "D", "text": "Elogiar las ventajas de las 'cajas negras' para optimizar la administración de justicia.", "is_correct": False, "distractor_type": "CONTRADICTION"},
        ],
        "explanation": {
            "correct_solution": "El autor busca refutar la creencia de neutralidad ('nada más alejado de la realidad') argumentando que los algoritmos reflejan datos sesgados históricamente.",
            "skill_evaluated": "Evaluar - Reflexionar sobre la postura y propósito del emisor."
        },
        "difficulty_estimate": 0.55,
    },

    # =========================================================================
    # 2. COMPETENCIA MATEMÁTICA 2 (M2)
    # =========================================================================
    {
        "id": "q-m2-log-01",
        "subtopic_id": "sub-m2-logaritmos",
        "skill_code": "RESOLVER_PROBLEMAS",
        "stem": "Si $\\log_2(x) + \\log_2(x - 2) = 3$, ¿cuál es el conjunto solución para los valores reales de $x$?",
        "options": [
            {"key": "A", "text": "$\\{4\\}$", "is_correct": True, "distractor_type": "CORRECT"},
            {"key": "B", "text": "$\\{-2, 4\\}$", "is_correct": False, "distractor_type": "EXTRANEOUS_ROOT_NOT_DISCARDED"},
            {"key": "C", "text": "$\\{2, 4\\}$", "is_correct": False, "distractor_type": "ALGEBRAIC_ERROR"},
            {"key": "D", "text": "$\\{8\\}$", "is_correct": False, "distractor_type": "POWER_CONFUSION"},
        ],
        "explanation": {
            "correct_solution": "Por propiedades de logaritmos: $\\log_2(x(x - 2)) = 3 \\implies x(x - 2) = 2^3 = 8$. Luego $x^2 - 2x - 8 = 0 \\implies (x - 4)(x + 2) = 0$. Dado que el argumento del logaritmo debe ser estrictamente positivo ($x > 0$ y $x - 2 > 0$), se descarta $x = -2$. Por tanto, el único valor válido es $x = 4$.",
            "skill_evaluated": "Resolver problemas con restricciones en el dominio real."
        },
        "difficulty_estimate": 0.65,
    },
    {
        "id": "q-m2-trig-01",
        "subtopic_id": "sub-m2-trigonometria",
        "skill_code": "MODELAR",
        "stem": "Para un ángulo agudo $\\alpha$ tal que $\\sin(\\alpha) = \\frac{3}{5}$, ¿cuál es el valor exacto de $\\tan(\\alpha) + \\cos(\\alpha)$?",
        "options": [
            {"key": "A", "text": "$\\frac{31}{20}$", "is_correct": True, "distractor_type": "CORRECT"},
            {"key": "B", "text": "$\\frac{7}{5}$", "is_correct": False, "distractor_type": "ARITHMETIC_ERROR"},
            {"key": "C", "text": "$\\frac{23}{20}$", "is_correct": False, "distractor_type": "COSINE_INVERSION"},
            {"key": "D", "text": "$\\frac{5}{3}$", "is_correct": False, "distractor_type": "RECIPROCAL_CONFUSION"},
        ],
        "explanation": {
            "correct_solution": "Por la identidad pitagórica, $\\cos^2(\\alpha) = 1 - \\sin^2(\\alpha) = 1 - \\frac{9}{25} = \\frac{16}{25} \\implies \\cos(\\alpha) = \\frac{4}{5}$. Luego, $\\tan(\\alpha) = \\frac{\\sin(\\alpha)}{\\cos(\\alpha)} = \\frac{3}{4}$. Sumando: $\\frac{3}{4} + \\frac{4}{5} = \\frac{15 + 16}{20} = \\frac{31}{20}$.",
            "skill_evaluated": "Modelar y aplicar identidades trigonométricas fundamentales."
        },
        "difficulty_estimate": 0.60,
    },
    {
        "id": "q-m2-inv-01",
        "subtopic_id": "sub-m2-funcion-inversa",
        "skill_code": "REPRESENTAR",
        "stem": "Sea la función biyectiva $f: \\mathbb{R} \\setminus \\{1\\} \\to \\mathbb{R} \\setminus \\{2\\}$ definida por $f(x) = \\frac{2x + 3}{x - 1}$. ¿Cuál es la expresión que define a su función inversa $f^{-1}(x)$?",
        "options": [
            {"key": "A", "text": "$f^{-1}(x) = \\frac{x + 3}{x - 2}$", "is_correct": True, "distractor_type": "CORRECT"},
            {"key": "B", "text": "$f^{-1}(x) = \\frac{x - 1}{2x + 3}$", "is_correct": False, "distractor_type": "RECIPROCAL_ONLY"},
            {"key": "C", "text": "$f^{-1}(x) = \\frac{2x - 3}{x + 1}$", "is_correct": False, "distractor_type": "SIGN_MISTAKE"},
            {"key": "D", "text": "$f^{-1}(x) = \\frac{x - 3}{x + 2}$", "is_correct": False, "distractor_type": "FACTORING_ERROR"},
        ],
        "explanation": {
            "correct_solution": "Hacemos $y = \\frac{2x + 3}{x - 1} \\implies y(x - 1) = 2x + 3 \\implies yx - y = 2x + 3 \\implies yx - 2x = y + 3 \\implies x(y - 2) = y + 3 \\implies x = \\frac{y + 3}{y - 2}$. Por tanto, $f^{-1}(x) = \\frac{x + 3}{x - 2}$.",
            "skill_evaluated": "Representar y despejar variables para determinar funciones inversas."
        },
        "difficulty_estimate": 0.70,
    },

    # =========================================================================
    # 3. CIENCIAS (BIOLOGÍA, FÍSICA, QUÍMICA)
    # =========================================================================
    {
        "id": "q-cie-bio-01",
        "subtopic_id": "sub-cie-genetica",
        "skill_code": "RESOLVER_PROBLEMAS",
        "stem": "En las plantas de arveja, el color amarillo de las semillas ($A$) es dominante sobre el verde ($a$). Si se cruzan dos plantas heterocigotas ($Aa \\times Aa$), ¿cuál es la probabilidad de que una planta descendiente elegida al azar tenga semillas verdes?",
        "options": [
            {"key": "A", "text": "$25\\%$", "is_correct": True, "distractor_type": "CORRECT"},
            {"key": "B", "text": "$50\\%$", "is_correct": False, "distractor_type": "HETEROZYGOUS_CONFUSION"},
            {"key": "C", "text": "$75\\%$", "is_correct": False, "distractor_type": "DOMINANT_PROBABILITY"},
            {"key": "D", "text": "$0\\%$", "is_correct": False, "distractor_type": "RECESSIVE_SUPPRESSION"},
        ],
        "explanation": {
            "correct_solution": "El cruzamiento monohíbrido $Aa \\times Aa$ genera las proporciones genotípicas: $1/4\\ AA$, $2/4\\ Aa$, $1/4\\ aa$. El fenotipo recesivo (semillas verdes) solo se expresa en el genotipo homocigoto recesivo ($aa$), que corresponde a $1/4 = 25\\%$.",
            "skill_evaluated": "Resolver problemas de genética mendeliana clásica y probabilidades."
        },
        "difficulty_estimate": 0.45,
    },
    {
        "id": "q-cie-fis-01",
        "subtopic_id": "sub-cie-mecanica",
        "skill_code": "MODELAR",
        "stem": "Un bloque de masa $m = 4\\ \\text{kg}$ reposa sobre una superficie horizontal lisa sin fricción. Si se le aplica una fuerza horizontal constante de $F = 20\\ \\text{N}$ durante $t = 3\\ \\text{s}$, ¿cuál es la velocidad final alcanzada por el bloque?",
        "options": [
            {"key": "A", "text": "$15\\ \\text{m/s}$", "is_correct": True, "distractor_type": "CORRECT"},
            {"key": "B", "text": "$5\\ \\text{m/s}$", "is_correct": False, "distractor_type": "ACCELERATION_ONLY"},
            {"key": "C", "text": "$60\\ \\text{m/s}$", "is_correct": False, "distractor_type": "FORCE_TIMES_TIME"},
            {"key": "D", "text": "$20\\ \\text{m/s}$", "is_correct": False, "distractor_type": "VELOCITY_EQUALS_FORCE"},
        ],
        "explanation": {
            "correct_solution": "Por la Segunda Ley de Newton: $a = \\frac{F}{m} = \\frac{20\\ \\text{N}}{4\\ \\text{kg}} = 5\\ \\text{m/s}^2$. Partiendo del reposo ($v_0 = 0$), la velocidad tras $3\\ \\text{s}$ es: $v = v_0 + a \\cdot t = 0 + 5\\ \\text{m/s}^2 \\cdot 3\\ \\text{s} = 15\\ \\text{m/s}$.",
            "skill_evaluated": "Modelar dinámica newtoniana y cinemática en una dimensión."
        },
        "difficulty_estimate": 0.40,
    },
    {
        "id": "q-cie-fis-02",
        "subtopic_id": "sub-cie-electricidad",
        "skill_code": "RESOLVER_PROBLEMAS",
        "stem": "Dos resistencias de $R_1 = 6\\ \\Omega$ y $R_2 = 12\\ \\Omega$ se conectan en paralelo a una batería que suministra una diferencia de potencial de $V = 24\\ \\text{V}$. ¿Cuál es la corriente total que entrega la batería al circuito?",
        "options": [
            {"key": "A", "text": "$6\\ \\text{A}$", "is_correct": True, "distractor_type": "CORRECT"},
            {"key": "B", "text": "$1.33\\ \\text{A}$", "is_correct": False, "distractor_type": "SERIES_RESISTANCE_CONFUSION"},
            {"key": "C", "text": "$4\\ \\text{A}$", "is_correct": False, "distractor_type": "EQUIVALENT_RESISTANCE_ONLY"},
            {"key": "D", "text": "$18\\ \\text{A}$", "is_correct": False, "distractor_type": "SUM_OF_RESISTANCES"},
        ],
        "explanation": {
            "correct_solution": "La resistencia equivalente en paralelo es: $\\frac{1}{R_{eq}} = \\frac{1}{6} + \\frac{1}{12} = \\frac{2 + 1}{12} = \\frac{3}{12} = \\frac{1}{4} \\implies R_{eq} = 4\\ \\Omega$. Aplicando la Ley de Ohm: $I_{total} = \\frac{V}{R_{eq}} = \\frac{24\\ \\text{V}}{4\\ \\Omega} = 6\\ \\text{A}$.",
            "skill_evaluated": "Resolver problemas de circuitos en paralelo y Ley de Ohm."
        },
        "difficulty_estimate": 0.50,
    },

    # =========================================================================
    # 4. HISTORIA Y CIENCIAS SOCIALES
    # =========================================================================
    {
        "id": "q-his-civ-01",
        "subtopic_id": "sub-his-ciudadania",
        "skill_code": "ARGUMENTAR",
        "stem": "¿Cuál es el principio fundamental del Estado de Derecho que establece que ninguna persona, institución o autoridad pública se encuentra por sobre las normas jurídicas vigentes?",
        "options": [
            {"key": "A", "text": "Principio de Supremacía Constitucional y Legalidad.", "is_correct": True, "distractor_type": "CORRECT"},
            {"key": "B", "text": "Principio de Subsidiariedad Económica.", "is_correct": False, "distractor_type": "ECONOMIC_DOCTRINE"},
            {"key": "C", "text": "Principio de Soberanía Absoluta del Parlamento.", "is_correct": False, "distractor_type": "MONARCHIC_CONFUSION"},
            {"key": "D", "text": "Principio de Centralismo Administrativo.", "is_correct": False, "distractor_type": "TERRITORIAL_CONCEPT"},
        ],
        "explanation": {
            "correct_solution": "El principio de legalidad e imperio de la ley consagra que todos los órganos del Estado y los ciudadanos deben someter su acción a la Constitución y a las normas dictadas conforme a ella, garantizando la igualdad ante la ley.",
            "skill_evaluated": "Argumentar sobre los pilares del régimen democrático y constitucional."
        },
        "difficulty_estimate": 0.35,
    },
    {
        "id": "q-his-siglo-01",
        "subtopic_id": "sub-his-siglo-xx",
        "skill_code": "RELACIONAR_INTERPRETAR",
        "stem": "Durante las primeras décadas del siglo XX en Chile, el proceso conocido como la 'Cuestión Social' estuvo estrechamente relacionado con:",
        "options": [
            {"key": "A", "text": "Las precarias condiciones de vida y laborales del proletariado urbano y salitrero derivadas de la migración campo-ciudad.", "is_correct": True, "distractor_type": "CORRECT"},
            {"key": "B", "text": "La implementación de las reformas agrarias impulsadas por la Alianza para el Progreso.", "is_correct": False, "distractor_type": "ANACHRONISM_1960S"},
            {"key": "C", "text": "La crisis de la deuda externa y la hiperinflación producida tras el crac de 1982.", "is_correct": False, "distractor_type": "ANACHRONISM_1980S"},
            {"key": "D", "text": "La firma de los primeros tratados de libre comercio con potencias asiáticas.", "is_correct": False, "distractor_type": "GLOBALIZATION_CONFUSION"},
        ],
        "explanation": {
            "correct_solution": "La Cuestión Social en Chile emergió a finales del s. XIX y comienzos del XX debido a la acelerada migración hacia las salitreras del norte y centros urbanos, generando hacinamiento (conventillos), insalubridad y ausencia de legislación laboral.",
            "skill_evaluated": "Relacionar procesos socioeconómicos históricos y sus causas estructurales."
        },
        "difficulty_estimate": 0.45,
    },
    {
        "id": "q-his-ddhh-01",
        "subtopic_id": "sub-his-ddhh",
        "skill_code": "ARGUMENTAR",
        "stem": "La Declaración Universal de los Derechos Humanos, aprobada por la Asamblea General de la ONU en 1948, estableció como característica esencial de estos derechos que son:",
        "options": [
            {"key": "A", "text": "Universales, inalienables e inherentes a toda persona por el solo hecho de su condición humana.", "is_correct": True, "distractor_type": "CORRECT"},
            {"key": "B", "text": "Condicionados al estatus migratorio y al pago regular de tributos en cada país.", "is_correct": False, "distractor_type": "CONDITIONAL_RESTRICTION"},
            {"key": "C", "text": "Renunciables voluntariamente mediante contratos privados entre particulares.", "is_correct": False, "distractor_type": "CIVIL_LAW_CONFUSION"},
            {"key": "D", "text": "Exclusivos de los ciudadanos pertenecientes a países signatarios de tratados bilaterales.", "is_correct": False, "distractor_type": "TERRITORIAL_ERROR"},
        ],
        "explanation": {
            "correct_solution": "El artículo 1 de la Declaración consagra que todos los seres humanos nacen libres e iguales en dignidad y derechos. Su universalidad e inalienabilidad garantizan que ningún Estado o particular puede desconocerlos ni revocar la condición intrínseca humana.",
            "skill_evaluated": "Argumentar sobre el marco internacional de protección a la dignidad humana."
        },
        "difficulty_estimate": 0.40,
    }
]
