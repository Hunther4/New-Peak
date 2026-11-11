import { useMemo, useState } from "react"
import { useNavigate } from "react-router"
import { useStore } from "../../store/store"

const GRUPOS = [
  { id: "obligatorias", titulo: "Pruebas obligatorias", materias: ["M1", "LECTURA"] },
  { id: "electivas", titulo: "Electivas", materias: ["M2", "CIENCIAS", "HISTORIA"] },
]
// Oculta el seleccionado si no hay datos; si hay datos, el total se recalcula sin esa materia.
const NOMBRES = {
  M1: "Matemáticas 1",
  LECTURA: "Competencia lectora",
  M2: "Matemáticas 2",
  CIENCIAS: "Ciencias",
  HISTORIA: "Historia",
}

export default function DualProgressRadar() {
  const navigate = useNavigate()
  const { paesSubtopicsList } = useStore()
  const [ocultas, setOcultas] = useState([])

  const alternar = (materia) => {
    const siguiente = ocultas.includes(materia) ? ocultas.filter((m) => m !== materia) : [...ocultas, materia]
    setOcultas(siguiente)
  }

  const agrupada = useMemo(() => {
    const lista = (paesSubtopicsList || []).filter((s) => !ocultas.includes(s.subject_code || s.subject || "M1"))
    return GRUPOS.map((grupo) => {
      const items = lista.filter((s) => grupo.materias.includes(s.subject_code || s.subject || "M1"))
      const promedio = items.length ? items.reduce((a, s) => a + (s.mastery || 0), 0) / items.length : 0
      const porMateria = grupo.materias.map((materia) => {
        const mItems = items.filter((s) => (s.subject_code || s.subject || "M1") === materia)
        const mProm = mItems.length ? mItems.reduce((a, s) => a + (s.mastery || 0), 0) / mItems.length : 0
        return {
          materia,
          score: Math.min(1000, Math.max(100, Math.round(100 + mProm * 900))),
          porcentaje: Math.round(mProm * 100),
        }
      })
      return { ...grupo, porMateria, score: Math.min(1000, Math.max(100, Math.round(100 + promedio * 900))), porcentaje: Math.round(promedio * 100) }
    })
  }, [paesSubtopicsList, ocultas])

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
      {agrupada.map((grupo) => (
        <div key={grupo.id} className="p-6 rounded-3xl bg-white/[0.02] border border-white/[0.06]">
          <div className="flex items-center justify-between mb-4">
            <h4 className="text-base font-bold text-white">{grupo.titulo}</h4>
            <button onClick={() => navigate("/paes")} className="text-xs font-semibold text-sky-400 hover:text-sky-300 cursor-pointer">Ver Academia</button>
          </div>

          <div className="flex flex-wrap gap-2 mb-4">
            {grupo.materias.map((materia) => (
              <button
                key={materia}
                type="button"
                onClick={() => alternar(materia)}
                aria-pressed={!ocultas.includes(materia)}
                className={`px-2.5 py-1 text-[11px] rounded-full border transition-colors cursor-pointer ${ocultas.includes(materia) ? "border-white/10 text-neutral-500" : "border-sky-500/30 text-sky-400 bg-sky-500/10"}`}
              >
                {ocultas.includes(materia) ? "＋ " : "● "}{NOMBRES[materia] || materia}
              </button>
            ))}
          </div>

          <div className="space-y-4 p-4 rounded-2xl bg-neutral-900/60 border border-white/[0.04]">
            <div className="flex items-baseline gap-1.5">
              <span className="text-[10px] uppercase font-mono tracking-wider text-sky-400 font-bold">Puntaje estimado</span>
              <span className="text-4xl leading-none font-black font-mono text-white">{grupo.score}</span>
              <span className="text-xs font-mono text-neutral-500">/ 1000 pts</span>
            </div>
            {grupo.porMateria.map((m) => (
              <div key={m.materia} className="space-y-1">
                <div className="flex justify-between text-xs">
                  <span className="text-neutral-300">{NOMBRES[m.materia] || m.materia}</span>
                  <span className="font-mono font-bold text-sky-300">{m.score} · {m.porcentaje}%</span>
                </div>
                <div className="w-full bg-neutral-800 h-2 rounded-full overflow-hidden">
                  <div className="bg-sky-500 h-full transition-all" style={{ width: `${m.porcentaje}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
