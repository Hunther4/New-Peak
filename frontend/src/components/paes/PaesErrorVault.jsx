import React, { useState, useEffect } from "react"
import { useStore } from "../../store/store"
import { MathRenderer } from "./MathRenderer"
import { PaesReadingStimulus } from "./PaesReadingStimulus"
import { PaesTwinVariantModal } from "./PaesTwinVariantModal"
import { playClickSound, playSuccessSound } from "../../utils/soundEffects"

export function PaesErrorVault({ onStartRevenge, onTwinVariant }) {
  const {
    paesErrorNotebook,
    paesErrorVault,
    loadErrorVault,
    fetchPaesErrorNotebook,
    paesActiveSubject,
    paesLoading,
  } = useStore()

  const [causeFilter, setCauseFilter] = useState("all")
  const [expandedId, setExpandedId] = useState(null)
  const [selectedTwinId, setSelectedTwinId] = useState(null)

  useEffect(() => {
    if (loadErrorVault) {
      loadErrorVault(1, paesActiveSubject)
    } else if (fetchPaesErrorNotebook) {
      fetchPaesErrorNotebook(paesActiveSubject)
    }
  }, [paesActiveSubject, loadErrorVault, fetchPaesErrorNotebook])

  const vaultData = paesErrorVault || paesErrorNotebook
  const totalErrors = vaultData?.total_errors || 0
  const items = vaultData?.items || []
  const byCause = vaultData?.by_distractor_type || vaultData?.by_mistake_cause || {}

  const filteredItems = items.filter((item) => {
    if (causeFilter === "all") return true
    return (item.last_mistake_cause || "").toUpperCase() === causeFilter.toUpperCase()
  })

  const getCauseBadge = (cause) => {
    const c = (cause || "CONCEPTUAL").toUpperCase()
    if (c === "CALCULO" || c === "ARITMETICO") {
      return { label: "Error de Cálculo", color: "bg-rose-500/15 border-rose-500/30 text-rose-300" }
    }
    if (c === "PROCEDIMENTAL") {
      return { label: "Falla de Procedimiento", color: "bg-amber-500/15 border-amber-500/30 text-amber-300" }
    }
    if (c === "INTERPRETACION") {
      return { label: "Mala Interpretación", color: "bg-sky-500/15 border-sky-500/30 text-sky-300" }
    }
    if (c === "LECTURA") {
      return { label: "Distractor de Lectura", color: "bg-purple-500/15 border-purple-500/30 text-purple-300" }
    }
    return { label: "Vacío Conceptual", color: "bg-orange-500/15 border-orange-500/30 text-orange-300" }
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header Banner */}
      <div className="p-6 rounded-3xl bg-neutral-900/60 border border-white/[0.08] backdrop-blur-xl flex flex-col md:flex-row items-start md:items-center justify-between gap-6 shadow-2xl">
        <div className="space-y-1.5">
          <div className="flex items-center gap-2">
            <span className="text-xl">🔥</span>
            <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-rose-400">
              Metacognición & Redención
            </span>
          </div>
          <h3 className="text-2xl font-black text-white tracking-tight">
            Cuaderno Negro de Errores ({totalErrors})
          </h3>
          <p className="text-xs text-neutral-400 max-w-xl">
            Cada error es oro puro para la PAES. Aquí se concentran los ítems donde caíste en un distractor oficial. Domínalos en una sesión de revancha para erradicar tus puntos ciegos.
          </p>
        </div>

        {totalErrors > 0 && (
          <button
            onClick={() => {
              playClickSound()
              onStartRevenge && onStartRevenge(Math.min(totalErrors, 10))
            }}
            className="px-6 py-3.5 rounded-2xl bg-gradient-to-r from-rose-500 to-orange-500 hover:from-rose-400 hover:to-orange-400 text-white font-bold text-xs shadow-lg shadow-rose-500/25 transition-all flex items-center gap-2 shrink-0 cursor-pointer"
          >
            <span>⚔️</span>
            <span>Iniciar Modo Revancha ({Math.min(totalErrors, 10)})</span>
          </button>
        )}
      </div>

      {/* Cause breakdown pills */}
      {totalErrors > 0 && (
        <div className="flex items-center gap-2 overflow-x-auto pb-2">
          <button
            onClick={() => setCauseFilter("all")}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${
              causeFilter === "all"
                ? "bg-white text-neutral-950 shadow-md"
                : "bg-neutral-900/80 border border-white/[0.06] text-neutral-400 hover:text-white"
            }`}
          >
            Todos ({totalErrors})
          </button>
          {Object.entries(byCause).map(([causeKey, count]) => {
            const badge = getCauseBadge(causeKey)
            const isSelected = causeFilter.toUpperCase() === causeKey.toUpperCase()
            return (
              <button
                key={causeKey}
                onClick={() => setCauseFilter(causeKey)}
                className={`px-3 py-1.5 rounded-xl text-xs font-bold border transition-all cursor-pointer flex items-center gap-1.5 ${
                  isSelected
                    ? "bg-rose-500/20 border-rose-500 text-rose-200 shadow-md shadow-rose-500/10"
                    : `${badge.color} hover:opacity-90`
                }`}
              >
                <span>{badge.label}</span>
                <span className="text-[10px] font-mono px-1.5 py-0.2 rounded-full bg-black/40">
                  {count}
                </span>
              </button>
            )
          })}
        </div>
      )}

      {/* Empty State */}
      {totalErrors === 0 && !paesLoading && (
        <div className="p-12 rounded-3xl bg-neutral-900/30 border border-white/[0.06] text-center space-y-4">
          <div className="text-4xl">🎯</div>
          <h4 className="text-lg font-bold text-white">¡Cuaderno de Errores Limpio!</h4>
          <p className="text-xs text-neutral-400 max-w-md mx-auto">
            No tienes errores activos sin superar en {paesActiveSubject || "esta materia"}. Rinde un ensayo o sesión de práctica para poner a prueba tus habilidades.
          </p>
        </div>
      )}

      {/* Errors Cards List */}
      <div className="space-y-4">
        {filteredItems.map((item, idx) => {
          const isExpanded = expandedId === item.question_id
          const causeBadge = getCauseBadge(item.last_mistake_cause)

          return (
            <div
              key={item.question_id}
              className="rounded-2xl bg-neutral-900/60 border border-white/[0.06] overflow-hidden transition-all hover:border-white/[0.12]"
            >
              {/* Card Summary Header */}
              <div
                onClick={() => setExpandedId(isExpanded ? null : item.question_id)}
                className="p-5 flex items-center justify-between gap-4 cursor-pointer select-none"
              >
                <div className="flex items-center gap-3.5">
                  <span className="w-8 h-8 rounded-xl bg-neutral-800 text-rose-400 font-mono font-bold text-xs flex items-center justify-center shrink-0 border border-rose-500/20">
                    {idx + 1}
                  </span>
                  <div>
                    <div className="flex items-center gap-2 text-xs mb-1">
                      <span className="font-semibold text-neutral-300">{item.subtopic_name}</span>
                      <span className="text-neutral-600">•</span>
                      <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${causeBadge.color}`}>
                        {causeBadge.label}
                      </span>
                      {item.failed_attempts_count > 1 && (
                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-rose-500/10 text-rose-300 border border-rose-500/20">
                          {item.failed_attempts_count} fallos
                        </span>
                      )}
                    </div>
                    <p className="text-sm font-medium text-neutral-200 line-clamp-1">
                      {item.stem.replace(/[$]/g, "")}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2.5 shrink-0">
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation()
                      setSelectedTwinId(item.question_id)
                    }}
                    className="px-3 py-1.5 rounded-xl bg-gradient-to-r from-rose-500 to-orange-500 hover:from-rose-400 hover:to-orange-400 text-white font-bold text-xs shadow-md shadow-rose-500/20 transition-all cursor-pointer flex items-center gap-1.5 shrink-0"
                  >
                    <span>⚡</span>
                    <span>Vengar Error</span>
                  </button>
                  <span className="text-neutral-500 text-xs transition-transform duration-200">
                    {isExpanded ? "▲" : "▼"}
                  </span>
                </div>
              </div>

              {/* Expanded Card Details */}
              {isExpanded && (
                <div className="p-6 pt-2 border-t border-white/[0.04] bg-neutral-950/40 space-y-6 animate-fade-in">
                  {/* Question Image or Stem */}
                  {item.image_url ? (
                    <div className="mb-4 rounded-2xl overflow-hidden border border-white/10 bg-white p-3 md:p-5 shadow-lg">
                      <img
                        src={item.image_url}
                        alt={`Pregunta ${item.question_id || ""}`}
                        className="w-full h-auto object-contain max-h-[450px] mx-auto rounded-lg select-none"
                        loading="lazy"
                      />
                    </div>
                  ) : (
                    <div className="p-4 rounded-xl bg-neutral-900/50 border border-white/[0.04] text-sm md:text-base text-neutral-100 leading-relaxed">
                      <MathRenderer text={item.stem} />
                    </div>
                  )}

                  {/* Options List */}
                  <div className="space-y-2">
                    <span className="text-xs font-bold uppercase tracking-wider text-neutral-400 block mb-2">
                      Alternativas & Distractores Oficiales
                    </span>
                    {item.options.map((opt) => {
                      const key = opt.id || opt.key
                      const wasSelected = item.last_selected_option === key
                      const isCorrect = opt.is_correct

                      let optClass = "bg-neutral-900/40 border-white/[0.04] text-neutral-400"
                      if (isCorrect) {
                        optClass = "bg-emerald-500/15 border-emerald-500 text-emerald-200 font-semibold"
                      } else if (wasSelected) {
                        optClass = "bg-rose-500/15 border-rose-500 text-rose-200"
                      }

                      return (
                        <div
                          key={key}
                          className={`p-3.5 rounded-xl border flex items-start gap-3 text-sm ${optClass}`}
                        >
                          <div className="font-bold font-mono text-xs w-6 h-6 rounded-lg bg-black/30 flex items-center justify-center shrink-0">
                            {key}
                          </div>
                          <div className="flex-1">
                            <MathRenderer text={opt.content || opt.text} />
                          </div>
                          {isCorrect && (
                            <span className="text-xs text-emerald-400 font-bold font-mono">
                              Correcta
                            </span>
                          )}
                          {wasSelected && !isCorrect && (
                            <span className="text-xs text-rose-400 font-bold font-mono">
                              Tu Selección Anterior
                            </span>
                          )}
                        </div>
                      )
                    })}
                  </div>

                  {/* Step-by-Step & Distractor Analysis */}
                  {item.explanation && (
                    <div className="space-y-3">
                      <div className="p-4 rounded-xl bg-sky-500/[0.06] border border-sky-500/20 space-y-2">
                        <div className="text-xs font-bold text-sky-400 uppercase tracking-wider flex items-center gap-1.5">
                          <span>💡</span>
                          <span>Resolución Pedagógica Paso a Paso</span>
                        </div>
                        <div className="text-xs text-neutral-300 leading-relaxed">
                          <MathRenderer
                            text={
                              item.explanation.step_by_step ||
                              item.explanation.correct_solution ||
                              item.explanation.short_summary ||
                              "Explicación oficial DEMRE."
                            }
                          />
                        </div>
                      </div>

                      {item.explanation.distractor_analysis && (
                        <div className="p-4 rounded-xl bg-amber-500/[0.06] border border-amber-500/20 space-y-2.5">
                          <div className="text-xs font-bold text-amber-400 uppercase tracking-wider flex items-center gap-1.5">
                            <span>🎯</span>
                            <span>Análisis de Distractores</span>
                          </div>
                          <div className="grid grid-cols-1 gap-2 pt-1">
                            {Object.entries(item.explanation.distractor_analysis).map(([optKey, desc]) => (
                              <div
                                key={optKey}
                                className="text-xs text-neutral-300 flex items-start gap-2 bg-neutral-900/60 p-2.5 rounded-lg border border-white/[0.04]"
                              >
                                <span className="font-bold font-mono px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 shrink-0">
                                  {optKey}
                                </span>
                                <span className="flex-1 text-neutral-300">
                                  <MathRenderer text={desc} />
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {selectedTwinId && (
        <PaesTwinVariantModal
          questionId={selectedTwinId}
          isOpen={Boolean(selectedTwinId)}
          onClose={() => {
            setSelectedTwinId(null)
            if (loadErrorVault) loadErrorVault(1, paesActiveSubject)
          }}
        />
      )}
    </div>
  )
}
