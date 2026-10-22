import React, { useEffect, useRef, useState } from "react"
import { MathRenderer } from "./MathRenderer"
import { PaesReadingStimulus } from "./PaesReadingStimulus"
import { PaesTwinVariantModal } from "./PaesTwinVariantModal"
import {
  playClickSound,
  playSuccessSound,
  playErrorSound,
  playStreakSound,
} from "../../utils/soundEffects"

export function PaesQuestionCard({
  question,
  selectedOption,
  onSelectOption,
  confidence,
  onChangeConfidence,
  onSubmit,
  lastResult,
  onNext,
  loading = false,
}) {
  const streakRef = useRef(0)
  const [showVariantModal, setShowVariantModal] = useState(false)

  useEffect(() => {
    if (lastResult) {
      if (lastResult.is_correct) {
        streakRef.current = (streakRef.current || 0) + 1
        const count = lastResult.streak_count || streakRef.current
        if (count >= 3) {
          playStreakSound(count)
        } else {
          playSuccessSound()
        }
      } else {
        streakRef.current = 0
        playErrorSound()
      }
    }
  }, [lastResult])

  if (!question) return null

  const isSubmitted = !!lastResult

  const handleOptionSelect = (key) => {
    if (isSubmitted) return
    playClickSound()
    if (onSelectOption) onSelectOption(key)
  }

  return (
    <div className="bg-neutral-900/60 border border-white/[0.08] rounded-2xl p-6 backdrop-blur-xl shadow-2xl">
      {/* Header tags */}
      <div className="flex items-center justify-between gap-2 mb-4 pb-3 border-b border-white/[0.06]">
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-bold uppercase tracking-wider text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-md border border-emerald-500/20">
            {question.provenance_type || "PAES"}
          </span>
          {question.is_pilot && (
            <span className="text-[11px] font-bold uppercase tracking-wider text-purple-400 bg-purple-500/10 px-2 py-0.5 rounded-md border border-purple-500/20">
              Experimental
            </span>
          )}
        </div>
        <div className="text-xs text-neutral-400 font-mono">
          Dificultad est: {Math.round((question.difficulty_estimate || 0.5) * 100)}%
        </div>
      </div>

      {/* Reading Stimulus / Text if available */}
      {question.stimulus_text && (
        <PaesReadingStimulus title={question.stimulus_title} text={question.stimulus_text} />
      )}

      {/* Official DEMRE Question Image or Text Fallback */}
      {question.image_url ? (
        <div className="mb-6 rounded-2xl overflow-hidden border border-white/10 bg-white p-3 md:p-5 shadow-2xl">
          <img
            src={question.image_url}
            alt={`Pregunta ${question.id || ""}`}
            className="w-full h-auto object-contain max-h-[550px] mx-auto rounded-lg select-none"
            loading="lazy"
          />
        </div>
      ) : (
        <div className="mb-6 text-sm md:text-base">
          <MathRenderer text={question.stem} />
        </div>
      )}

      {/* Options */}
      <div className="space-y-3 mb-6">
        {question.options.map((opt) => {
          const key = opt.key || opt.id
          const isSelected = selectedOption === key

          let optionStyle = "bg-neutral-800/40 border-white/[0.08] hover:bg-neutral-800/70 text-neutral-200"
          if (isSubmitted) {
            if (lastResult.correct_option === key) {
              optionStyle = "bg-emerald-500/20 border-emerald-500 text-emerald-200"
            } else if (isSelected && !lastResult.is_correct) {
              optionStyle = "bg-rose-500/20 border-rose-500 text-rose-200"
            } else {
              optionStyle = "bg-neutral-900/40 border-white/[0.04] text-neutral-500 opacity-60"
            }
          } else if (isSelected) {
            optionStyle = "bg-emerald-500/15 border-emerald-500 text-white ring-1 ring-emerald-500/50"
          }

          return (
            <button
              key={key}
              type="button"
              disabled={isSubmitted}
              onClick={() => handleOptionSelect(key)}
              className={`w-full text-left p-4 rounded-xl border transition-all flex items-start gap-3.5 ${optionStyle}`}
            >
              <div
                className={`w-7 h-7 rounded-lg flex items-center justify-center font-bold text-xs shrink-0 ${
                  isSelected
                    ? "bg-emerald-500 text-black shadow-md shadow-emerald-500/25"
                    : "bg-neutral-800 text-neutral-300 border border-white/[0.08]"
                }`}
              >
                {key}
              </div>
              <div className="flex-1 pt-0.5 text-sm">
                <MathRenderer text={opt.content || opt.text} />
              </div>
            </button>
          )
        })}
      </div>

      {/* Metacognitive Confidence Selector */}
      {!isSubmitted && (
        <div className="mb-6 p-4 rounded-xl bg-neutral-800/30 border border-white/[0.04] flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div>
            <div className="text-xs font-bold text-neutral-300 uppercase tracking-wider">
              Seguridad Metacognitiva
            </div>
            <div className="text-[11px] text-neutral-500">
              Alimenta el cálculo de dominio FSRS y detección de descuidos.
            </div>
          </div>
          <div className="flex items-center gap-1.5">
            {[1, 2, 3, 4, 5].map((lvl) => (
              <button
                key={lvl}
                type="button"
                onClick={() => onChangeConfidence(lvl)}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  confidence === lvl
                    ? "bg-emerald-500 text-black shadow-sm"
                    : "bg-neutral-800 text-neutral-400 hover:text-white"
                }`}
              >
                {lvl}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Submit / Next Actions */}
      <div className="flex items-center justify-end gap-3 pt-4 border-t border-white/[0.06]">
        {!isSubmitted ? (
          <button
            type="button"
            disabled={!selectedOption || loading}
            onClick={onSubmit}
            className="px-6 py-3 bg-gradient-to-r from-emerald-500 to-green-600 hover:from-emerald-400 hover:to-green-500 disabled:opacity-40 text-black font-bold text-sm rounded-xl shadow-lg shadow-emerald-500/20 transition-all"
          >
            {loading ? "Evaluando..." : "Confirmar Respuesta"}
          </button>
        ) : (
          <div className="w-full">
            {/* Feedback alert */}
            <div
              className={`p-4 rounded-xl border mb-4 ${
                lastResult.is_correct
                  ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300"
                  : "bg-rose-500/10 border-rose-500/30 text-rose-300"
              }`}
            >
              <div className="flex items-center gap-2 font-bold text-sm mb-1.5">
                <span>{lastResult.is_correct ? "✅ ¡Correcto!" : "❌ Respuesta incorrecta"}</span>
                {lastResult.distractor_cause && (
                  <span className="text-[11px] px-2 py-0.5 rounded bg-rose-500/20 text-rose-200 uppercase font-mono">
                    Causa: {lastResult.distractor_cause}
                  </span>
                )}
              </div>
              
              {/* Step-by-step pedagogical explanation */}
              {(lastResult.explanation?.step_by_step || lastResult.explanation?.correct_solution || lastResult.explanation?.short_summary) && (
                <div className="mt-2 pt-2 border-t border-white/[0.08] text-xs leading-relaxed">
                  <div className="font-semibold text-neutral-300 mb-1 flex items-center gap-1.5">
                    <span>💡</span>
                    <span>Resolución Pedagógica:</span>
                  </div>
                  <MathRenderer
                    text={
                      lastResult.explanation.step_by_step ||
                      lastResult.explanation.correct_solution ||
                      lastResult.explanation.short_summary
                    }
                  />
                </div>
              )}

              {/* Distractor Analysis breakdown */}
              {lastResult.explanation?.distractor_analysis && (
                <div className="mt-2.5 pt-2 border-t border-white/[0.08] text-xs">
                  <div className="font-semibold text-amber-300 mb-1 flex items-center gap-1.5">
                    <span>🎯</span>
                    <span>Análisis de Alternativas:</span>
                  </div>
                  <div className="space-y-1.5 mt-1.5">
                    {Object.entries(lastResult.explanation.distractor_analysis).map(([optKey, desc]) => (
                      <div key={optKey} className="flex items-start gap-1.5 text-neutral-300 bg-neutral-900/60 p-2 rounded-lg">
                        <span className="font-bold font-mono px-1 rounded bg-amber-500/20 text-amber-300 shrink-0">
                          {optKey}
                        </span>
                        <span className="flex-1">
                          <MathRenderer text={desc} />
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
              {!lastResult.is_correct ? (
                <div className="flex items-center gap-3 flex-wrap">
                  <button
                    type="button"
                    onClick={() => setShowVariantModal(true)}
                    className="px-4 py-2.5 bg-gradient-to-r from-rose-500 to-orange-500 hover:from-rose-400 hover:to-orange-400 text-white font-bold text-xs rounded-xl shadow-lg shadow-rose-500/25 transition-all cursor-pointer flex items-center gap-1.5 shrink-0"
                  >
                    <span>⚡</span>
                    <span>Vengar Error</span>
                  </button>
                  <div className="text-xs text-rose-300/90 flex items-center gap-1.5 font-medium">
                    <span>🔥</span>
                    <span>Registrado en tu <strong>Cuaderno de Errores</strong>.</span>
                  </div>
                </div>
              ) : (
                <div />
              )}
              <div className="flex justify-end ml-auto">
                <button
                  type="button"
                  onClick={onNext}
                  className="px-6 py-3 bg-white text-black hover:bg-neutral-200 font-bold text-sm rounded-xl shadow-lg transition-all cursor-pointer"
                >
                  Siguiente Pregunta →
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {showVariantModal && (
        <PaesTwinVariantModal
          questionId={question.id}
          isOpen={showVariantModal}
          onClose={() => setShowVariantModal(false)}
        />
      )}
    </div>
  )
}
