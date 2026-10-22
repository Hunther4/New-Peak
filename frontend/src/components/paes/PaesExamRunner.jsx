import React, { useState, useEffect, useRef } from "react"
import { useStore } from "../../store/store"
import { MathRenderer } from "./MathRenderer"
import { PaesReadingStimulus } from "./PaesReadingStimulus"
import {
  playClickSound,
  playSuccessSound,
  isSoundMuted,
  toggleSoundMute,
} from "../../utils/soundEffects"

export function PaesExamRunner() {
  const {
    paesSessionId,
    paesQuestions,
    paesCurrentIndex,
    paesActiveQuestion,
    paesExamAnswers,
    paesExamFlags,
    paesExamTimeLimitMinutes,
    paesLoading,
    paesError,
    paesActiveSubject,
    paesSubtopic,
    setExamAnswer,
    toggleExamFlag,
    jumpToPaesQuestion,
    finalizePaesExam,
    exitPaesExam,
  } = useStore()

  // Countdown timer in seconds
  const [secondsRemaining, setSecondsRemaining] = useState(
    (paesExamTimeLimitMinutes || 32) * 60
  )
  const [showConfirmModal, setShowConfirmModal] = useState(false)
  const [showExitModal, setShowExitModal] = useState(false)
  const [lastSavedTimeStr, setLastSavedTimeStr] = useState(null)
  const [questionElapsedSeconds, setQuestionElapsedSeconds] = useState(0)
  const [soundMuted, setSoundMuted] = useState(isSoundMuted())
  const questionStartTimeRef = useRef(Date.now())

  // Keep sound mute state synchronized
  useEffect(() => {
    const handleMuteChange = (e) => {
      if (e.detail?.muted !== undefined) {
        setSoundMuted(e.detail.muted)
      } else {
        setSoundMuted(isSoundMuted())
      }
    }
    window.addEventListener("peak-sound-mute-change", handleMuteChange)
    window.addEventListener("storage", handleMuteChange)
    return () => {
      window.removeEventListener("peak-sound-mute-change", handleMuteChange)
      window.removeEventListener("storage", handleMuteChange)
    }
  }, [])

  // Track pacing per question
  useEffect(() => {
    setQuestionElapsedSeconds(0)
    questionStartTimeRef.current = Date.now()
  }, [paesCurrentIndex])

  useEffect(() => {
    const qTimer = setInterval(() => {
      setQuestionElapsedSeconds(Math.round((Date.now() - questionStartTimeRef.current) / 1000))
    }, 1000)
    return () => clearInterval(qTimer)
  }, [])

  // Autoguardado & Recuperación de emergencia ante recarga
  useEffect(() => {
    if (!paesSessionId) return
    const backupKey = `paes_exam_backup_${paesSessionId}`
    try {
      const savedRaw = localStorage.getItem(backupKey)
      if (savedRaw) {
        const backup = JSON.parse(savedRaw)
        if (backup && backup.sessionId === paesSessionId && backup.savedAt) {
          const elapsedSecs = Math.floor((Date.now() - backup.savedAt) / 1000)
          const remaining = Math.max(0, (backup.secondsRemaining || 0) - elapsedSecs)
          setSecondsRemaining(remaining)
          if (remaining <= 1) {
            finalizePaesExam()
          }
        }
      }
    } catch {
      // Ignore storage read errors
    }
  }, [paesSessionId, finalizePaesExam])

  // Guardado periódico automático en localStorage
  useEffect(() => {
    if (!paesSessionId) return
    const backupKey = `paes_exam_backup_${paesSessionId}`
    try {
      const data = {
        sessionId: paesSessionId,
        answers: paesExamAnswers,
        flags: paesExamFlags,
        secondsRemaining,
        savedAt: Date.now(),
      }
      localStorage.setItem(backupKey, JSON.stringify(data))
      const now = new Date()
      setLastSavedTimeStr(
        `${now.getHours().toString().padStart(2, "0")}:${now.getMinutes().toString().padStart(2, "0")}:${now.getSeconds().toString().padStart(2, "0")}`
      )
    } catch {
      // LocalStorage lleno o restringido
    }
  }, [paesSessionId, paesExamAnswers, paesExamFlags, Math.floor(secondsRemaining / 5)])

  // Keep timer in sync if timeLimitMinutes updates after session start
  useEffect(() => {
    if (paesExamTimeLimitMinutes) {
      setSecondsRemaining(paesExamTimeLimitMinutes * 60)
    }
  }, [paesExamTimeLimitMinutes])

  // Timer interval
  useEffect(() => {
    const timer = setInterval(() => {
      setSecondsRemaining((prev) => {
        if (prev <= 1) {
          clearInterval(timer)
          finalizePaesExam()
          return 0
        }
        return prev - 1
      })
    }, 1000)
    return () => clearInterval(timer)
  }, [finalizePaesExam])

  // Track time spent per question on question change
  const currentQuestionId = paesActiveQuestion?.id
  const selectedOption = currentQuestionId
    ? paesExamAnswers[currentQuestionId]?.selectedOption || null
    : null
  const isFlagged = currentQuestionId
    ? paesExamFlags.includes(currentQuestionId)
    : false

  const handleSelectOption = (key) => {
    if (!currentQuestionId) return
    playClickSound()
    setExamAnswer(currentQuestionId, key)
  }

  const handleNavigate = (newIdx) => {
    if (newIdx < 0 || newIdx >= paesQuestions.length) return
    playClickSound()
    const elapsedSeconds = Math.round(
      (Date.now() - questionStartTimeRef.current) / 1000
    )
    if (currentQuestionId) {
      setExamAnswer(currentQuestionId, selectedOption, elapsedSeconds)
    }
    questionStartTimeRef.current = Date.now()
    jumpToPaesQuestion(newIdx)
  }

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (showConfirmModal) return
      const key = e.key.toUpperCase()

      if (["A", "B", "C", "D"].includes(key)) {
        handleSelectOption(key)
      } else if (["1", "2", "3", "4"].includes(key)) {
        const mapping = { "1": "A", "2": "B", "3": "C", "4": "D" }
        handleSelectOption(mapping[key])
      } else if (e.key === "ArrowRight") {
        handleNavigate(paesCurrentIndex + 1)
      } else if (e.key === "ArrowLeft") {
        handleNavigate(paesCurrentIndex - 1)
      } else if (e.key === "f" || e.key === "F") {
        if (currentQuestionId) toggleExamFlag(currentQuestionId)
      }
    }
    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [paesCurrentIndex, currentQuestionId, selectedOption, showConfirmModal])

  // Format MM:SS or HH:MM:SS
  const formatTime = (secs) => {
    const h = Math.floor(secs / 3600)
    const m = Math.floor((secs % 3600) / 60)
    const s = secs % 60
    if (h > 0) {
      return `${h}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`
    }
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`
  }

  const totalQuestions = paesQuestions.length
  const answeredCount = Object.values(paesExamAnswers).filter(
    (a) => a.selectedOption
  ).length
  const isUrgent = secondsRemaining < 300 // < 5 mins

  if (!paesActiveQuestion) {
    return (
      <div className="max-w-md mx-auto my-24 p-8 rounded-3xl bg-neutral-900/80 border border-white/[0.08] text-center space-y-4 animate-fade-in">
        <div className="w-10 h-10 border-2 border-sky-400 border-t-transparent rounded-full animate-spin mx-auto" />
        <h3 className="text-sm font-bold text-white">Preparando Simulacro Oficial</h3>
        <p className="text-xs text-neutral-400">Cargando batería de preguntas DEMRE calibradas...</p>
      </div>
    )
  }

  const subjectTitle = paesSubtopic || `Simulacro Oficial DEMRE ${paesActiveSubject || "M1"}`

  return (
    <div className="max-w-6xl mx-auto space-y-6 animate-fade-in pb-12">
      {/* Error Alert if finalize failed */}
      {paesError && (
        <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center justify-between gap-4">
          <span>Error al procesar el ensayo: {paesError}</span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => finalizePaesExam()}
              className="px-3 py-1.5 bg-rose-500 hover:bg-rose-400 text-white font-bold rounded-xl transition-all cursor-pointer"
            >
              Reintentar
            </button>
            <button
              onClick={() => exitPaesExam()}
              className="px-3 py-1.5 bg-neutral-800 hover:bg-neutral-700 text-neutral-300 font-bold rounded-xl transition-all cursor-pointer"
            >
              Salir
            </button>
          </div>
        </div>
      )}

      {/* Top Exam Header */}
      <header className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-2xl bg-neutral-900/80 border border-white/[0.08] backdrop-blur-md">
        <div className="flex items-center gap-3">
          <span className="p-2.5 rounded-xl bg-sky-500/10 text-sky-400 font-bold text-lg">
            ⏱️
          </span>
          <div>
            <h3 className="text-sm font-bold text-white tracking-tight">
              {subjectTitle}
            </h3>
            <div className="flex items-center gap-3">
              <p className="text-xs text-neutral-400">
                Respondidas: <strong className="text-emerald-400">{answeredCount}</strong> de {totalQuestions}
              </p>
              <span className="text-neutral-600 hidden sm:inline">•</span>
              <div className="hidden sm:flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[11px] font-medium font-mono">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                <span>Autoguardado {lastSavedTimeStr ? `(${lastSavedTimeStr})` : "Activo"}</span>
              </div>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Accessible Sound Switch */}
          <button
            type="button"
            data-testid="exam-sound-toggle"
            onClick={() => {
              const nextMuted = toggleSoundMute()
              setSoundMuted(nextMuted)
              if (!nextMuted) playClickSound()
            }}
            aria-label={soundMuted ? "Activar efectos de sonido" : "Silenciar efectos de sonido"}
            title={soundMuted ? "Sonido silenciado (clic para activar)" : "Sonido activo (clic para silenciar)"}
            className={`px-3 py-2 rounded-xl border text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer ${
              soundMuted
                ? "bg-neutral-800/80 border-white/[0.08] text-neutral-400 hover:text-white"
                : "bg-emerald-500/15 border-emerald-500/30 text-emerald-300 hover:bg-emerald-500/25"
            }`}
          >
            <span className="text-sm" aria-hidden="true">{soundMuted ? "🔇" : "🔊"}</span>
            <span className="hidden sm:inline font-mono">{soundMuted ? "Mute" : "Audio"}</span>
          </button>

          {/* Live Timer */}
          <div
            className={`px-4 py-2 rounded-xl border font-mono font-bold text-sm tracking-wider flex items-center gap-2 ${
              isUrgent
                ? "bg-rose-500/15 border-rose-500 text-rose-300 animate-pulse"
                : "bg-neutral-800/80 border-white/[0.08] text-white"
            }`}
          >
            <span className="text-xs text-neutral-400 font-sans font-normal">Restante:</span>
            <span>{formatTime(secondsRemaining)}</span>
          </div>

          <button
            onClick={() => setShowExitModal(true)}
            className="px-3.5 py-2 bg-neutral-800 hover:bg-neutral-700 text-neutral-400 hover:text-rose-300 text-xs font-bold rounded-xl border border-white/[0.08] transition-all cursor-pointer"
          >
            Abandonar
          </button>

          <button
            onClick={() => setShowConfirmModal(true)}
            className="px-4 py-2 bg-emerald-500 hover:bg-emerald-400 text-neutral-950 font-bold text-xs rounded-xl transition-all shadow-lg shadow-emerald-500/20 cursor-pointer"
          >
            Finalizar Ensayo ➔
          </button>
        </div>
      </header>

      {/* Main Grid: Navigation Sidebar (Left) + Question Workspace (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Navigation Grid (4 Cols on desktop) */}
        <div className="lg:col-span-4 p-5 rounded-2xl bg-neutral-900/60 border border-white/[0.08] flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4 pb-3 border-b border-white/[0.06]">
              <span className="text-xs font-bold uppercase tracking-wider text-neutral-300">
                Matriz de Respuestas
              </span>
              <span className="text-[11px] text-neutral-400 font-mono">
                {answeredCount}/{totalQuestions}
              </span>
            </div>

            {/* Quick Legend */}
            <div className="flex items-center gap-3 text-[10px] text-neutral-400 mb-4">
              <span className="flex items-center gap-1">
                <span className="w-2.5 h-2.5 rounded bg-emerald-500" /> Respondida
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2.5 h-2.5 rounded bg-neutral-800 border border-white/20" /> Pendiente
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2.5 h-2.5 rounded bg-amber-500" /> Revisar 🚩
              </span>
            </div>

            {/* Question Buttons Matrix */}
            <div className="grid grid-cols-5 gap-2 max-h-[420px] overflow-y-auto pr-1">
              {paesQuestions.map((q, idx) => {
                const isCurrent = idx === paesCurrentIndex
                const hasAnswer = !!paesExamAnswers[q.id]?.selectedOption
                const isQFlagged = paesExamFlags.includes(q.id)

                let btnClass = "bg-neutral-850 border-white/[0.08] text-neutral-400 hover:border-white/20"
                if (hasAnswer) {
                  btnClass = "bg-emerald-500/20 border-emerald-500/60 text-emerald-300 font-bold"
                }
                if (isQFlagged) {
                  btnClass = "bg-amber-500/25 border-amber-500 text-amber-200 font-bold"
                }
                if (isCurrent) {
                  btnClass += " ring-2 ring-sky-400 border-sky-400 text-white"
                }

                return (
                  <button
                    key={q.id}
                    onClick={() => handleNavigate(idx)}
                    className={`h-9 rounded-xl border text-xs font-mono transition-all flex items-center justify-center relative cursor-pointer ${btnClass}`}
                  >
                    <span>{idx + 1}</span>
                    {isQFlagged && (
                      <span className="absolute -top-1 -right-1 text-[9px]">🚩</span>
                    )}
                  </button>
                )
              })}
            </div>
          </div>

          <div className="pt-4 mt-4 border-t border-white/[0.06] flex items-center justify-between text-[11px] text-neutral-400">
            <span>Atajo: [A, B, C, D] o [1, 2, 3, 4]</span>
            <span>[F] Marcar 🚩</span>
          </div>
        </div>

        {/* Question Workspace (8 Cols) */}
        <div className="lg:col-span-8 p-6 md:p-8 rounded-2xl bg-neutral-900/60 border border-white/[0.08] flex flex-col justify-between backdrop-blur-xl">
          <div>
            {/* Question Header */}
            <div className="flex items-center justify-between gap-3 mb-6 pb-4 border-b border-white/[0.06]">
              <div className="flex items-center gap-2">
                <span className="px-2.5 py-1 rounded-lg bg-sky-500/10 border border-sky-500/20 text-sky-400 text-xs font-bold font-mono">
                  Pregunta {paesCurrentIndex + 1} de {totalQuestions}
                </span>
                {paesActiveQuestion.is_pilot && (
                  <span className="px-2 py-0.5 rounded-md bg-purple-500/10 border border-purple-500/20 text-purple-400 text-[10px] font-bold uppercase tracking-wider">
                    Piloto DEMRE
                  </span>
                )}
              </div>

              <button
                onClick={() => toggleExamFlag(currentQuestionId)}
                className={`px-3 py-1.5 rounded-xl border text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer ${
                  isFlagged
                    ? "bg-amber-500/20 border-amber-500 text-amber-300"
                    : "bg-neutral-800/60 border-white/[0.08] text-neutral-400 hover:text-white"
                }`}
              >
                <span>🚩</span>
                <span>{isFlagged ? "Marcada para Revisión" : "Marcar para Revisar"}</span>
              </button>
            </div>

            {/* Barra de Ritmo ("Pacing Bar") por Ítem Activo */}
            {(() => {
              const SUGGESTED_QUESTION_SECONDS = 180 // 3 minutos
              const isPacingExceeded = questionElapsedSeconds > SUGGESTED_QUESTION_SECONDS
              const pacingProgress = Math.min(100, Math.round((questionElapsedSeconds / SUGGESTED_QUESTION_SECONDS) * 100))

              return (
                <div
                  data-testid="paes-pacing-bar"
                  className={`mb-6 p-3.5 rounded-2xl border transition-all duration-300 ${
                    isPacingExceeded
                      ? "bg-amber-500/10 border-amber-500/40 text-amber-200 shadow-md shadow-amber-500/5"
                      : "bg-neutral-800/40 border-white/[0.06] text-neutral-300"
                  }`}
                >
                  <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                    <div className="flex items-center gap-2">
                      <span className={`text-sm ${isPacingExceeded ? "text-amber-400" : "text-sky-400"}`}>
                        ⏱️
                      </span>
                      <span className="text-xs font-semibold">
                        {isPacingExceeded ? (
                          <span className="text-amber-300 font-bold flex items-center gap-1.5">
                            <span>Tiempo sugerido excedido: ¡Gestiona tu ritmo DEMRE!</span>
                          </span>
                        ) : (
                          <span>
                            Tiempo en esta pregunta: <strong className="font-mono text-white">{formatTime(questionElapsedSeconds)}</strong>{" "}
                            <span className="text-neutral-500 font-normal">/ 03:00 sugerido</span>
                          </span>
                        )}
                      </span>
                    </div>

                    <div className="flex items-center gap-2 text-[11px] font-mono">
                      {isPacingExceeded ? (
                        <span className="text-amber-300 font-bold bg-amber-500/20 px-2 py-0.5 rounded-md border border-amber-500/30">
                          {formatTime(questionElapsedSeconds)} ({Math.floor(questionElapsedSeconds / 60)}m {questionElapsedSeconds % 60}s)
                        </span>
                      ) : (
                        <span className="text-neutral-400">
                          {pacingProgress}% del tiempo sugerido
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Progress Bar Track */}
                  <div className="w-full h-1.5 bg-neutral-800/90 rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-all duration-500 ease-out ${
                        isPacingExceeded
                          ? "bg-amber-400 shadow-sm shadow-amber-400/50"
                          : "bg-gradient-to-r from-sky-400 to-emerald-400"
                      }`}
                      style={{ width: `${pacingProgress}%` }}
                    />
                  </div>

                  {isPacingExceeded && (
                    <div className="mt-2.5 pt-2 border-t border-amber-500/20 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
                      <p className="text-[11px] text-amber-200/80 leading-relaxed">
                        Has superado los 3 minutos recomendados para esta pregunta. En la PAES real, es clave avanzar y asegurar preguntas directas.
                      </p>
                      {!isFlagged && (
                        <button
                          type="button"
                          onClick={() => {
                            playClickSound()
                            toggleExamFlag(currentQuestionId)
                          }}
                          className="self-start sm:self-auto px-2.5 py-1 bg-amber-500/20 hover:bg-amber-500/30 text-amber-100 text-[11px] font-bold rounded-lg border border-amber-500/30 transition-all cursor-pointer whitespace-nowrap"
                        >
                          Marcar 🚩 y avanzar
                        </button>
                      )}
                    </div>
                  )}
                </div>
              )
            })()}

            {/* Reading Stimulus if present */}
            {paesActiveQuestion.stimulus_text && (
              <PaesReadingStimulus
                title={paesActiveQuestion.stimulus_title}
                text={paesActiveQuestion.stimulus_text}
              />
            )}

            {/* Official DEMRE Question Image or Text Fallback */}
            {paesActiveQuestion.image_url ? (
              <div className="mb-8 rounded-2xl overflow-hidden border border-white/10 bg-white p-3 md:p-5 shadow-2xl">
                <img
                  src={paesActiveQuestion.image_url}
                  alt={`Pregunta ${paesActiveQuestion.id || ""}`}
                  className="w-full h-auto object-contain max-h-[550px] mx-auto rounded-lg select-none"
                  loading="lazy"
                />
              </div>
            ) : (
              <div className="text-base text-neutral-100 leading-relaxed mb-8 select-text">
                <MathRenderer text={paesActiveQuestion.stem} />
              </div>
            )}

            {/* Options List */}
            <div className="space-y-3 mb-8">
              {paesActiveQuestion.options.map((opt) => {
                const key = opt.id || opt.key
                const isSelected = selectedOption === key

                return (
                  <button
                    key={key}
                    onClick={() => handleSelectOption(key)}
                    className={`w-full text-left p-4 rounded-2xl border transition-all flex items-start gap-4 cursor-pointer ${
                      isSelected
                        ? "bg-sky-500/15 border-sky-500 text-white ring-1 ring-sky-500/50 shadow-md shadow-sky-500/10"
                        : "bg-neutral-800/30 border-white/[0.06] hover:bg-neutral-800/60 text-neutral-300"
                    }`}
                  >
                    <div
                      className={`w-8 h-8 rounded-xl flex items-center justify-center font-bold text-xs shrink-0 transition-colors ${
                        isSelected
                          ? "bg-sky-400 text-neutral-950 font-black shadow"
                          : "bg-neutral-800 text-neutral-400 border border-white/[0.08]"
                      }`}
                    >
                      {key}
                    </div>
                    <div className="flex-1 pt-1 text-sm md:text-base">
                      <MathRenderer text={opt.content || opt.text} />
                    </div>
                  </button>
                )
              })}
            </div>
          </div>

          {/* Navigation Controls */}
          <div className="flex items-center justify-between gap-4 pt-6 border-t border-white/[0.06]">
            <button
              onClick={() => handleNavigate(paesCurrentIndex - 1)}
              disabled={paesCurrentIndex === 0}
              className="px-4 py-2.5 rounded-xl border border-white/[0.08] bg-neutral-800/80 hover:bg-neutral-750 disabled:opacity-40 text-neutral-300 text-xs font-bold transition-all cursor-pointer"
            >
              ← Anterior
            </button>

            <div className="text-xs font-mono text-neutral-500 hidden sm:block">
              Navegá con [←] y [→]
            </div>

            {paesCurrentIndex < totalQuestions - 1 ? (
              <button
                onClick={() => handleNavigate(paesCurrentIndex + 1)}
                className="px-5 py-2.5 rounded-xl bg-white hover:bg-neutral-200 text-neutral-950 text-xs font-bold transition-all shadow cursor-pointer"
              >
                Siguiente →
              </button>
            ) : (
              <button
                onClick={() => setShowConfirmModal(true)}
                className="px-5 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-neutral-950 text-xs font-bold transition-all shadow-lg shadow-emerald-500/20 cursor-pointer"
              >
                Revisar y Entregar ➔
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Confirmation Modal */}
      {showConfirmModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div className="max-w-md w-full p-6 rounded-3xl bg-neutral-900 border border-white/[0.1] space-y-5 shadow-2xl">
            <div className="flex items-center gap-3">
              <span className="p-3 rounded-2xl bg-amber-500/10 text-amber-400 text-xl font-bold">
                ⚠️
              </span>
              <div>
                <h4 className="text-base font-bold text-white">¿Finalizar el Ensayo?</h4>
                <p className="text-xs text-neutral-400">
                  Una vez entregado, se calculará tu puntaje oficial DEMRE {paesActiveSubject || "M1"}.
                </p>
              </div>
            </div>

            <div className="p-4 rounded-2xl bg-neutral-800/50 border border-white/[0.04] space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-neutral-400">Preguntas Respondidas:</span>
                <strong className="text-emerald-400 font-mono">{answeredCount}</strong>
              </div>
              <div className="flex justify-between">
                <span className="text-neutral-400">Preguntas Omitidas:</span>
                <strong className="text-amber-400 font-mono">{totalQuestions - answeredCount}</strong>
              </div>
              <div className="flex justify-between">
                <span className="text-neutral-400">Marcadas para Revisión:</span>
                <strong className="text-sky-400 font-mono">{paesExamFlags.length}</strong>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={() => setShowConfirmModal(false)}
                className="flex-1 py-3 rounded-xl bg-neutral-800 hover:bg-neutral-700 text-neutral-300 text-xs font-bold transition-colors cursor-pointer"
              >
                Seguir Respondiendo
              </button>
              <button
                onClick={() => {
                  if (currentQuestionId) {
                    const elapsedSeconds = Math.round(
                      (Date.now() - questionStartTimeRef.current) / 1000
                    )
                    setExamAnswer(currentQuestionId, selectedOption, elapsedSeconds)
                  }
                  setShowConfirmModal(false)
                  finalizePaesExam()
                }}
                disabled={paesLoading}
                className="flex-1 py-3 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-neutral-950 text-xs font-bold transition-all shadow-lg shadow-emerald-500/20 cursor-pointer"
              >
                {paesLoading ? "Calculando..." : "Sí, Entregar Ensayo"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Exit / Abandon Modal */}
      {showExitModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div className="max-w-md w-full p-6 rounded-3xl bg-neutral-900 border border-white/[0.1] space-y-5 shadow-2xl">
            <div className="flex items-center gap-3">
              <span className="p-3 rounded-2xl bg-rose-500/10 text-rose-400 text-xl font-bold">
                🚪
              </span>
              <div>
                <h4 className="text-base font-bold text-white">¿Abandonar el Ensayo?</h4>
                <p className="text-xs text-neutral-400">
                  Tu progreso no será computado ni se registrará puntaje psicométrico.
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={() => setShowExitModal(false)}
                className="flex-1 py-3 rounded-xl bg-neutral-800 hover:bg-neutral-700 text-neutral-300 text-xs font-bold transition-colors cursor-pointer"
              >
                Continuar Ensayo
              </button>
              <button
                onClick={() => {
                  setShowExitModal(false)
                  exitPaesExam()
                }}
                className="flex-1 py-3 rounded-xl bg-rose-500 hover:bg-rose-400 text-white text-xs font-bold transition-all shadow-lg shadow-rose-500/20 cursor-pointer"
              >
                Sí, Abandonar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

