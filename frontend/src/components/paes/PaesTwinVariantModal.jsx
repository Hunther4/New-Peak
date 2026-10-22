import React, { useState, useEffect } from "react"
import { useStore } from "../../store/store"
import { MathRenderer } from "./MathRenderer"
import { playSelectTap, playSuccessChime, playErrorTone } from "../../utils/soundEffects"

export function PaesTwinVariantModal({ questionId, isOpen, onClose }) {
  const { fetchQuestionVariant } = useStore()
  const [variant, setVariant] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [selectedOption, setSelectedOption] = useState(null)
  const [isEvaluated, setIsEvaluated] = useState(false)
  const [revealed, setRevealed] = useState(false)

  const loadVariant = async (seed = null) => {
    if (!questionId) return
    setLoading(true)
    setError(null)
    setSelectedOption(null)
    setIsEvaluated(false)
    setRevealed(false)
    try {
      const data = await fetchQuestionVariant(questionId, seed)
      setVariant(data)
    } catch (err) {
      setError(err.message || "Error al generar variante paramétrica")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (isOpen && questionId) {
      loadVariant()
    } else {
      setVariant(null)
      setSelectedOption(null)
      setIsEvaluated(false)
      setRevealed(false)
    }
  }, [isOpen, questionId])

  if (!isOpen) return null

  const handleSelect = (key) => {
    if (isEvaluated) return
    playSelectTap()
    setSelectedOption(key)
  }

  const handleEvaluate = () => {
    if (!selectedOption || !variant) return
    setIsEvaluated(true)
    setRevealed(true)
    const opt = variant.options.find((o) => (o.id || o.key) === selectedOption)
    if (opt?.is_correct) {
      playSuccessChime()
    } else {
      playErrorTone()
    }
  }

  const isCurrentCorrect = Boolean(
    isEvaluated &&
    variant?.options.find((o) => (o.id || o.key) === selectedOption)?.is_correct
  )

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fade-in">
      <div className="relative w-full max-w-2xl bg-neutral-900 border border-rose-500/30 rounded-3xl p-6 md:p-8 shadow-2xl overflow-y-auto max-h-[90vh] space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between gap-4 pb-4 border-b border-white/[0.08]">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="text-xl">⚡</span>
              <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-rose-400 bg-rose-500/10 px-2 py-0.5 rounded border border-rose-500/20">
                Ciclo de Redención • SymPy
              </span>
            </div>
            <h3 className="text-xl font-black text-white tracking-tight">
              Vengar Error — Variante Gemela Paramétrica
            </h3>
            <p className="text-xs text-neutral-400">
              Mismo concepto evaluado pero con datos numéricos cambiados para comprobar si superaste el punto ciego.
            </p>
          </div>

          <button
            onClick={onClose}
            className="w-8 h-8 rounded-xl bg-neutral-800 hover:bg-neutral-700 text-neutral-400 hover:text-white flex items-center justify-center text-sm font-bold transition-all cursor-pointer shrink-0"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        {loading ? (
          <div className="py-16 text-center space-y-3">
            <div className="w-10 h-10 border-2 border-rose-500 border-t-transparent rounded-full animate-spin mx-auto" />
            <p className="text-xs text-neutral-400 font-mono">
              Generando ejercicio gemelo analítico con SymPy...
            </p>
          </div>
        ) : error ? (
          <div className="p-6 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-center space-y-3">
            <p className="text-sm font-bold">{error}</p>
            <button
              onClick={() => loadVariant()}
              className="px-4 py-2 bg-rose-500 text-white rounded-xl font-bold text-xs hover:bg-rose-400"
            >
              Reintentar
            </button>
          </div>
        ) : variant ? (
          <div className="space-y-6">
            {/* Stem */}
            <div className="p-5 rounded-2xl bg-neutral-950/80 border border-white/[0.08] text-sm md:text-base text-neutral-100 leading-relaxed font-medium">
              <MathRenderer text={variant.stem} />
            </div>

            {/* Options */}
            <div className="grid grid-cols-1 gap-2.5">
              {variant.options.map((opt) => {
                const key = opt.id || opt.key
                const isSelected = selectedOption === key
                const isCorrect = opt.is_correct

                let style = "bg-neutral-950/60 border-white/[0.08] hover:border-white/[0.2] text-neutral-200"
                if (isEvaluated) {
                  if (isCorrect) {
                    style = "bg-emerald-500/15 border-emerald-500 text-emerald-300 shadow-md shadow-emerald-500/10"
                  } else if (isSelected) {
                    style = "bg-rose-500/15 border-rose-500 text-rose-300"
                  } else {
                    style = "bg-neutral-950/40 border-white/[0.04] text-neutral-500 opacity-60"
                  }
                } else if (isSelected) {
                  style = "bg-rose-500/15 border-rose-500 text-rose-200 ring-2 ring-rose-500/30"
                }

                return (
                  <button
                    key={key}
                    type="button"
                    disabled={isEvaluated}
                    onClick={() => handleSelect(key)}
                    className={`w-full p-4 rounded-xl border transition-all text-left flex items-center gap-3.5 cursor-pointer disabled:cursor-default ${style}`}
                  >
                    <span
                      className={`w-7 h-7 rounded-lg flex items-center justify-center font-bold text-xs font-mono shrink-0 transition-colors ${
                        isEvaluated && isCorrect
                          ? "bg-emerald-500 text-neutral-950"
                          : isEvaluated && isSelected
                            ? "bg-rose-500 text-white"
                            : isSelected
                              ? "bg-rose-500 text-white"
                              : "bg-neutral-800 text-neutral-400"
                      }`}
                    >
                      {key}
                    </span>
                    <div className="flex-1 min-w-0 text-sm">
                      <MathRenderer text={opt.content || opt.text} />
                    </div>
                    {isEvaluated && isCorrect && (
                      <span className="text-xs font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-md border border-emerald-500/20">
                        ✓ Correcta
                      </span>
                    )}
                    {isEvaluated && isSelected && !isCorrect && (
                      <span className="text-xs font-bold text-rose-400 bg-rose-500/10 px-2 py-0.5 rounded-md border border-rose-500/20">
                        ✗ Tu elección
                      </span>
                    )}
                  </button>
                )
              })}
            </div>

            {/* Evaluation Alert */}
            {isEvaluated && (
              <div
                className={`p-4 rounded-2xl border flex items-center justify-between gap-4 animate-fade-in ${
                  isCurrentCorrect
                    ? "bg-emerald-500/15 border-emerald-500/30 text-emerald-200"
                    : "bg-rose-500/15 border-rose-500/30 text-rose-200"
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <span className="text-2xl">{isCurrentCorrect ? "🔥" : "⚠️"}</span>
                  <div>
                    <h4 className="text-sm font-bold">
                      {isCurrentCorrect
                        ? "¡ERROR VENGADO CON ÉXITO!"
                        : "Respuesta incorrecta en la variante"}
                    </h4>
                    <p className="text-xs text-neutral-300">
                      {isCurrentCorrect
                        ? "Has dominado el principio conceptual detrás del ejercicio."
                        : "Revisa la resolución paso a paso para despejar la duda."}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Step-by-Step Explanation */}
            {revealed && variant.explanation && (
              <div className="p-5 rounded-2xl bg-neutral-950/90 border border-white/[0.08] space-y-3 animate-fade-in text-xs text-neutral-300">
                <div className="font-bold text-sky-400 flex items-center gap-1.5 uppercase tracking-wider text-[11px]">
                  <span>💡</span>
                  <span>Solucionario Pedagógico Paso a Paso</span>
                </div>
                {variant.explanation.step_by_step && (
                  <div className="p-3 rounded-xl bg-neutral-900 border border-white/[0.04]">
                    <MathRenderer text={variant.explanation.step_by_step} />
                  </div>
                )}
                {variant.explanation.key_concept && (
                  <div className="text-neutral-300">
                    <strong className="text-sky-300 block mb-0.5">Concepto Clave:</strong>
                    {variant.explanation.key_concept}
                  </div>
                )}
                {variant.explanation.frequent_mistake && (
                  <div className="text-neutral-400">
                    <strong className="text-amber-400 block mb-0.5">Distractor / Error común:</strong>
                    {variant.explanation.frequent_mistake}
                  </div>
                )}
              </div>
            )}

            {/* Bottom Actions */}
            <div className="flex items-center justify-between pt-4 border-t border-white/[0.08] flex-wrap gap-3">
              <button
                type="button"
                onClick={() => loadVariant(Math.floor(Math.random() * 100000))}
                className="px-4 py-2.5 bg-neutral-800 hover:bg-neutral-700 text-neutral-200 font-bold text-xs rounded-xl border border-white/[0.08] transition-all cursor-pointer flex items-center gap-1.5"
              >
                <span>🎲</span>
                <span>Probar Otra Variante</span>
              </button>

              <div className="flex items-center gap-2.5">
                {!isEvaluated ? (
                  <button
                    type="button"
                    disabled={!selectedOption}
                    onClick={handleEvaluate}
                    className="px-6 py-2.5 bg-gradient-to-r from-rose-500 to-orange-500 hover:from-rose-400 hover:to-orange-400 disabled:opacity-40 text-white font-bold text-xs rounded-xl shadow-lg shadow-rose-500/20 transition-all cursor-pointer disabled:cursor-not-allowed flex items-center gap-1.5"
                  >
                    <span>⚡</span>
                    <span>Comprobar Venganza</span>
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={onClose}
                    className="px-6 py-2.5 bg-white text-neutral-950 font-bold text-xs rounded-xl hover:bg-neutral-200 transition-all cursor-pointer"
                  >
                    Cerrar
                  </button>
                )}
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  )
}
