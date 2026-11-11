import { useMemo, useEffect } from "react"
import { useNavigate } from "react-router"
import { useStore } from "../store/store"
import { PageTransition } from "../components/ui/PageTransition"
import { icons } from "../components/ui/icons"

export default function CognitiveGym() {
  const navigate = useNavigate()
  const { skills, fetchSkills } = useStore()

  useEffect(() => {
    if (fetchSkills && (!skills || skills.length === 0)) {
      fetchSkills()
    }
  }, [fetchSkills, skills])

  const gymGames = useMemo(() => {
    const list = skills || []
    const nBack = list.find((s) => s.skill_type === "dual_n_back" || s.slug === "dual-n-back")
    const memory = list.find((s) => s.skill_type === "memory_number" || s.slug === "memory-number")
    const math = list.find((s) => s.skill_type === "math_thinking" || s.slug === "math-thinking")
    const iq = list.find((s) => s.skill_type === "iq_practice" || s.slug === "iq-practice")

    return [
      {
        id: "dual_n_back",
        title: "Dual N-Back Científico",
        category: "Memoria Operativa",
        levelText: `Nivel N = ${nBack?.current_level ? Math.round(nBack.current_level) : 1}`,
        staircase: "Progresión adaptativa",
        icon: <icons.brain className="w-6 h-6 text-blue-400" />,
        accent: "from-blue-500 to-indigo-600",
        borderGlow: "group-hover:border-blue-500/40",
        bgGlow: "bg-blue-500/10",
        pill: "Visuoespacial + Fonológico",
        description:
          "Estimulación simultánea visoespacial y auditiva para expandir la capacidad de la memoria de trabajo y el control inhibitorio.",
        stats: [
          { label: "Canal", value: "Dual (Audio/Visual)" },
          { label: "Target", value: "Precisión ≥ 80%" },
        ],
        skillId: nBack?.id,
      },
      {
        id: "memory_number",
        title: "Memory Digit Span",
        category: "Capacidad Nemotécnica",
        levelText: `Fase ${Math.round(memory?.current_level || 1)} · Span ${Math.round(memory?.current_level || 1) * 4}d`,
        staircase: "Escalera Ericsson SF 4→80",
        icon: <icons.streak className="w-6 h-6 text-purple-400" />,
        accent: "from-purple-500 to-pink-600",
        borderGlow: "group-hover:border-purple-500/40",
        bgGlow: "bg-purple-500/10",
        pill: "Chunking & Mnemotecnia",
        description:
          "Entrenamiento de retención y agrupamiento de dígitos para desarrollar representaciones mentales y superar el límite de memoria a corto plazo.",
        stats: [
          { label: "Fases", value: "1 a 7 Progresivas" },
          { label: "Estrategias", value: "Chunking / Fonemas" },
        ],
        skillId: memory?.id,
      },
      {
        id: "math_thinking",
        title: "Pensamiento Matemático",
        category: "Aritmética & Descomposición",
        levelText: `Nivel ${Math.round(math?.current_level || 1)} / 10`,
        staircase: "Staircase Aritmético",
        icon: <icons.math1 className="w-6 h-6 text-emerald-400" />,
        accent: "from-emerald-500 to-teal-600",
        borderGlow: "group-hover:border-emerald-500/40",
        bgGlow: "bg-emerald-500/10",
        pill: "Velocidad & Fluidez",
        description:
          "Automatización de operaciones intermedias y cálculo mental rápido para resolver problemas con mayor agilidad cognitiva.",
        stats: [
          { label: "Niveles", value: "1 al 10 Adaptativo" },
          { label: "Resolución", value: "Paso a paso guiado" },
        ],
        skillId: math?.id,
      },
      {
        id: "iq_practice",
        title: "Matrices & Razonamiento IQ",
        category: "Inteligencia Fluida (Gf)",
        levelText: `Nivel ${Math.round(iq?.current_level || 1)} / 10`,
        staircase: "Escalera Raven Inductiva",
        icon: <icons.focus className="w-6 h-6 text-amber-400" />,
        accent: "from-amber-500 to-orange-600",
        borderGlow: "group-hover:border-amber-500/40",
        bgGlow: "bg-amber-500/10",
        pill: "Matrices & Analogías",
        description:
          "Reconocimiento de secuencias, simetrías y transformaciones lógicas mediante matrices inductivas con selección rápida.",
        stats: [
          { label: "Modalidad", value: "A/B/C/D Atajos" },
          { label: "Prefetching", value: "Cero latencia" },
        ],
        skillId: iq?.id,
      },
    ]
  }, [skills])

  const handleLaunch = (game) => {
    navigate(`/practice/${game.id}${game.skillId ? `?skillId=${game.skillId}` : ""}`)
  }

  return (
    <PageTransition>
      <div className="space-y-8">
        {/* Header Hero */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 lg:p-8 rounded-3xl bg-white/[0.02] border border-white/[0.06] backdrop-blur-xl">
          <div className="space-y-2 max-w-2xl">
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono uppercase font-bold px-2.5 py-1 rounded-full bg-purple-500/15 border border-purple-500/30 text-purple-400">
                Entrenamiento
              </span>
              <span className="text-xs text-neutral-400 font-medium">
                4 ejercicios
              </span>
            </div>
            <h1 className="text-2xl lg:text-3xl font-black tracking-tight text-white">
              Entrena tus capacidades
            </h1>
            <p className="text-xs lg:text-sm text-neutral-400 leading-relaxed">
              Cada sesión ajusta la dificultad según tu avance: un acierto sube, un error baja. Practica en tu ritmo y en el punto justo donde más aprendes.
            </p>
          </div>

          <div className="p-4 rounded-2xl bg-neutral-900/70 border border-white/[0.06] shrink-0 text-center md:text-right">
            <span className="text-[10px] uppercase font-mono text-neutral-400 block font-semibold">
              Regla de Ericsson
            </span>
            <span className="text-sm font-bold text-white mt-1 block">
              1↑ Correcto / 1↓ Error
            </span>
            <span className="text-[11px] text-emerald-400 font-medium mt-0.5 block">
              Frontera de confort activa
            </span>
          </div>
        </div>

        {/* 4 exercises grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {gymGames.map((game) => (
            <div
              key={game.id}
              className={`group relative p-6 lg:p-8 rounded-3xl bg-white/[0.02] border border-white/[0.06] ${game.borderGlow} transition-all duration-300 flex flex-col justify-between hover:shadow-2xl hover:bg-white/[0.04]`}
            >
              <div className="space-y-4">
                {/* Top badges */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className={`w-12 h-12 rounded-2xl ${game.bgGlow} flex items-center justify-center text-2xl shadow-inner`}>
                      {game.icon}
                    </span>
                    <div>
                      <span className="text-[10px] uppercase font-mono font-bold tracking-wider text-neutral-400 block">
                        {game.category}
                      </span>
                      <h3 className="text-lg font-bold text-white tracking-tight group-hover:text-emerald-300 transition-colors">
                        {game.title}
                      </h3>
                    </div>
                  </div>
                  <span className="text-xs font-mono font-bold text-neutral-300 px-2.5 py-1 rounded-xl bg-white/[0.06] border border-white/[0.08]">
                    {game.levelText}
                  </span>
                </div>

                {/* Subtitle tag */}
                <div className="flex items-center gap-2">
                  <span className="text-[10px] uppercase font-mono font-bold px-2 py-0.5 rounded-md bg-white/[0.04] text-neutral-400 border border-white/[0.06]">
                    {game.staircase}
                  </span>
                  <span className="text-[10px] uppercase font-mono font-bold px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    {game.pill}
                  </span>
                </div>

                {/* Description */}
                <p className="text-xs text-neutral-400 leading-relaxed">
                  {game.description}
                </p>

                {/* Stats row */}
                <div className="grid grid-cols-2 gap-3 py-3 border-y border-white/[0.04]">
                  {game.stats.map((st) => (
                    <div key={st.label} className="space-y-0.5">
                      <span className="text-[10px] text-neutral-500 uppercase font-semibold">
                        {st.label}
                      </span>
                      <p className="text-xs font-semibold text-neutral-200">
                        {st.value}
                      </p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Launch Button */}
              <button
                onClick={() => handleLaunch(game)}
                className={`mt-6 w-full py-3.5 rounded-2xl bg-gradient-to-r ${game.accent} text-white font-extrabold text-sm tracking-wide shadow-xl hover:scale-[1.02] active:scale-[0.98] transition-all flex items-center justify-center gap-2 cursor-pointer`}
              >
                <span>Entrenar habilidad</span>
                <icons.next size={16} />
              </button>
            </div>
          ))}
        </div>
      </div>
    </PageTransition>
  )
}
