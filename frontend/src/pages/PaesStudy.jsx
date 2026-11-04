import React, { useEffect, useState, useMemo } from "react"
import { useSearchParams } from "react-router"
import { useStore } from "../store/store"
import { FsrsStatusWidget } from "../components/paes/FsrsStatusWidget"
import { PaesQuestionCard } from "../components/paes/PaesQuestionCard"
import { SocraticTutorDrawer } from "../components/paes/SocraticTutorDrawer"
import { PaesExamRunner } from "../components/paes/PaesExamRunner"
import { PaesExamResults } from "../components/paes/PaesExamResults"
import { MathRenderer } from "../components/paes/MathRenderer"
import { PaesErrorVault } from "../components/paes/PaesErrorVault"
import { CruchAdmissionSimulator } from "../components/paes/CruchAdmissionSimulator"
import { PaesWeeklyRoutineBar } from "../components/paes/PaesWeeklyRoutineBar"
import { isSoundMuted, toggleSoundMute } from "../utils/soundEffects"
import { api } from "../api/client"
import { icons } from "../components/ui/icons"

// Every tab that the study hub can render. The list is the single source of
// truth for the navigation bar and for the ?tab= query parameter.
const PAES_TAB_IDS = ["exams", "error_vault", "cruch", "curriculum", "parametric", "fsrs"]

export default function PaesStudy() {

  const [searchParams] = useSearchParams()
  const subtopicParam = searchParams.get("subtopic")
  const tabParam = searchParams.get("tab")

  const {
    paesSessionId,
    paesSubtopic,
    paesQuestions,
    paesCurrentIndex,
    paesActiveQuestion,
    paesSelectedOption,
    paesConfidence,
    paesLastResult,
    paesFsrsStatus,
    paesSubtopicsList,
    paesSocraticHints,
    paesLoading,
    paesError,
    paesExamActive,
    paesExamResults,
    paesActiveSubject,
    paesErrorNotebook,
    fetchPaesSubjects,
    setPaesActiveSubject,
    fetchPaesFsrsStatus,
    fetchPaesSubtopics,
    fetchPaesErrorNotebook,
    loadErrorVault,
    startRevengeSession,
    startPaesSession,
    startPaesExam,
    selectPaesOption,
    setPaesConfidence,
    submitPaesAttempt,
    nextPaesQuestion,
    requestSocraticHint,
    resetPaesSession,
    exitPaesExam,
    restoreActiveExamSession,
  } = useStore()

  // Derive initial tab from query params if available
  const initialTab = (subtopicParam && subtopicParam !== "undefined" && subtopicParam !== "null")
    ? "curriculum"
    : (PAES_TAB_IDS.includes(tabParam) ? tabParam : "exams")

  // Tab: "exams" | "error_vault" | "cruch" | "curriculum" | "parametric" | "fsrs"
  const [activeTab, setActiveTab] = useState(initialTab)

  const [soundMuted, setSoundMuted] = useState(isSoundMuted())
  const [parametricQuestion, setParametricQuestion] = useState(null)
  const [parametricLoading, setParametricLoading] = useState(false)
  const [parametricRevealed, setParametricRevealed] = useState(false)
  const [parametricTemplate, setParametricTemplate] = useState("PARAM-M1-ALG-01")
  const [parametricSelected, setParametricSelected] = useState(null)
  const [parametricEvaluated, setParametricEvaluated] = useState(false)

  useEffect(() => {
    if (restoreActiveExamSession) {
      restoreActiveExamSession()
    }
  }, [])

  useEffect(() => {
    if (fetchPaesSubjects) fetchPaesSubjects()
    fetchPaesFsrsStatus(1, paesActiveSubject || "M1")
    fetchPaesSubtopics(1, paesActiveSubject || "M1")
    if (loadErrorVault) {
      loadErrorVault(1, paesActiveSubject || "M1")
    } else if (fetchPaesErrorNotebook) {
      fetchPaesErrorNotebook(paesActiveSubject || "M1")
    }
  }, [paesActiveSubject])

  const handleStartSubtopic = (slug) => {
    startPaesSession("PRACTICE", slug, 10, paesActiveSubject || "M1")
  }

  const handleStartGeneral = () => {
    if (subtopicParam && subtopicParam !== "undefined" && subtopicParam !== "null") {
      startPaesSession("PRACTICE", subtopicParam, 10, paesActiveSubject || "M1")
      return
    }
    const queue = paesFsrsStatus?.capped_review_queue
    const firstDue = Array.isArray(queue) ? (Array.isArray(queue[0]) ? queue[0][0] : queue[0]) : null
    if (firstDue?.slug) {
      startPaesSession("PRACTICE", firstDue.slug, 10, paesActiveSubject || "M1")
    } else {
      startPaesSession("PRACTICE", null, 10, paesActiveSubject || "M1")
    }
  }

  const handleGenerateParametric = async (templateCode = parametricTemplate) => {
    setParametricLoading(true)
    setParametricRevealed(false)
    setParametricSelected(null)
    setParametricEvaluated(false)
    try {
      const q = await api.paes.getParametricQuestion(templateCode)
      setParametricQuestion(q)
    } catch (e) {
      console.error(e)
    } finally {
      setParametricLoading(false)
    }
  }

const SUBJECTS_LIST = [
  { code: "M1", name: "Matemática 1", icon: "math1", badge: "Obligatoria", timePerQ: "2 min 09 seg / preg" },
  { code: "LECTURA", name: "Competencia Lectora", icon: "reading", badge: "Obligatoria", timePerQ: "2 min 18 seg / preg" },
  { code: "M2", name: "Matemática 2", icon: "math2", badge: "Específica", timePerQ: "2 min 32 seg / preg" },
  { code: "CIENCIAS", name: "Ciencias", icon: "science", badge: "Electiva", timePerQ: "2 min 00 seg / preg" },
  { code: "HISTORIA", name: "Historia y Cs. Sociales", icon: "history", badge: "Electiva", timePerQ: "1 min 50 seg / preg" },
]

const SUBJECT_EXAMS_CONFIG = {
  M1: {
    mini: { count: 15, time: 32, label: "15 Preguntas balanceadas en los 4 ejes DEMRE M1." },
    mid: { count: 30, time: 65, label: "30 Preguntas para medir ritmo y resistencia." },
    full: { count: 65, time: 140, label: "Simulacro Oficial Completo M1 (60 evaluadas + 5 piloto)." },
  },
  LECTURA: {
    mini: { count: 15, time: 35, label: "15 Preguntas con textos continuos y discontinuos." },
    mid: { count: 30, time: 70, label: "30 Preguntas con las 3 habilidades oficiales DEMRE." },
    full: { count: 65, time: 150, label: "Simulacro Oficial Completo de Comprensión Lectora (150 min)." },
  },
  M2: {
    mini: { count: 15, time: 35, label: "15 Preguntas de trigonometría, logaritmos y funciones." },
    mid: { count: 30, time: 75, label: "30 Preguntas de nivel 3° y 4° Medio avanzado." },
    full: { count: 55, time: 140, label: "Simulacro Oficial Completo Matemática 2 (55 preguntas)." },
  },
  CIENCIAS: {
    mini: { count: 20, time: 40, label: "20 Preguntas de Biología, Física y Química." },
    mid: { count: 40, time: 80, label: "40 Preguntas de módulo común y electivo." },
    full: { count: 80, time: 160, label: "Simulacro Oficial Completo de Ciencias (80 preguntas)." },
  },
  HISTORIA: {
    mini: { count: 15, time: 30, label: "15 Preguntas de análisis de fuentes y ciudadanía." },
    mid: { count: 30, time: 60, label: "30 Preguntas de Historia de Chile, economía y territorio." },
    full: { count: 65, time: 120, label: "Simulacro Oficial Completo de Historia (65 preguntas)." },
  },
}

  // Group subtopics dynamically by Ejes
  const subtopicsByEje = useMemo(() => {
    const list = paesSubtopicsList || []
    const groups = {}
    list.forEach((sub) => {
      const eje = sub.eje_name || "General"
      if (!groups[eje]) groups[eje] = []
      groups[eje].push(sub)
    })
    return groups
  }, [paesSubtopicsList])

  // 1. If currently in EXAM MODE: show PaesExamRunner
  if (paesExamActive) {
    return <PaesExamRunner key={paesSessionId || "exam-runner"} />
  }

  const currentSubject = SUBJECTS_LIST.find((s) => s.code === (paesActiveSubject || "M1")) || SUBJECTS_LIST[0]
  const currentExamConfig = SUBJECT_EXAMS_CONFIG[currentSubject.code] || SUBJECT_EXAMS_CONFIG["M1"]

  // 2. If viewing EXAM RESULTS: show PaesExamResults
  if (paesExamResults) {
    return (
      <PaesExamResults
        onNewExam={() => startPaesExam(currentExamConfig.mini.count, currentSubject.code)}
        onBackToStudy={() => exitPaesExam()}
      />
    )
  }

  return (
    <div className="max-w-5xl mx-auto py-4 animate-fade-in pb-16">
      {/* 5 Official PAES Subjects Switcher Pills */}
      <div className="flex items-center gap-2 mb-6 p-1.5 rounded-2xl bg-neutral-900/60 border border-white/[0.06] overflow-x-auto">
        {SUBJECTS_LIST.map((subj) => {
          const isActive = (paesActiveSubject || "M1") === subj.code
          const SubjectIcon = icons[subj.icon]
          return (
            <button
              key={subj.code}
              onClick={() => setPaesActiveSubject(subj.code)}
              className={`px-3 py-2.5 rounded-xl text-xs font-semibold transition-colors flex items-center gap-2 whitespace-nowrap cursor-pointer ${
                isActive
                  ? "bg-sky-500 text-neutral-950"
                  : "text-neutral-400 hover:text-white hover:bg-white/[0.04]"
              }`}
            >
              <SubjectIcon size={16} strokeWidth={1.8} />
              <span>{subj.name}</span>
              <span
                className={`text-[10px] px-1.5 py-0.5 rounded-md font-mono ${
                  isActive ? "bg-black/20 text-neutral-900" : "bg-white/[0.06] text-neutral-400"
                }`}
              >
                {subj.badge}
              </span>
            </button>
          )
        })}
      </div>

      {/* Top Main Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            {(() => { const SubjectIcon = icons[currentSubject.icon]; return <SubjectIcon size={22} strokeWidth={1.8} className="text-sky-400" /> })()}
            <h1 className="text-xl sm:text-2xl font-semibold text-white tracking-tight">
              {currentSubject.name}
            </h1>
            <span className="text-[11px] font-mono px-2 py-0.5 rounded-md bg-sky-500/10 border border-sky-500/20 text-sky-400 font-semibold">
              {currentSubject.code}
            </span>
          </div>
          <p className="text-xs md:text-sm text-neutral-400">
            Preguntas oficiales DEMRE 2026, con corrección inmediata y seguimiento de errores.
          </p>
        </div>

        <div className="flex items-center gap-2 self-start md:self-auto">
          <button
            onClick={() => setSoundMuted(toggleSoundMute())}
            className="btn btn-ghost btn-sm"
            title={soundMuted ? "Activar efectos sonoros" : "Silenciar audio"}
          >
            {soundMuted ? <icons.volumeOff size={16} strokeWidth={1.8} /> : <icons.volumeOn size={16} strokeWidth={1.8} />}
            <span className="hidden sm:inline">{soundMuted ? "Silenciado" : "Audio"}</span>
          </button>

          {paesSessionId && !paesExamActive && (
            <button
              onClick={resetPaesSession}
              className="btn btn-secondary btn-sm"
            >
              <icons.back size={15} strokeWidth={1.8} />
              Salir de práctica
            </button>
          )}
        </div>
      </div>

      {/* Error Alert */}
      {paesError && (
        <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs mb-6 flex items-center justify-between">
          <span>{paesError}</span>
          <button
            onClick={() => {
              fetchPaesFsrsStatus(1, paesActiveSubject || "M1")
              fetchPaesSubtopics(1, paesActiveSubject || "M1")
            }}
            className="text-xs underline font-semibold text-rose-400 cursor-pointer"
          >
            Reintentar
          </button>
        </div>
      )}

      {/* REGULAR PRACTICE SESSION IN PROGRESS */}
      {paesSessionId && paesActiveQuestion ? (
        <div className="space-y-6">
          <div className="flex items-center justify-between text-xs text-neutral-400 mb-2 font-mono">
            <span>
              Subtema: <strong className="text-white">{paesSubtopic || "General M1"}</strong>
            </span>
            <span>
              Pregunta {paesCurrentIndex + 1} de {paesQuestions.length}
            </span>
          </div>

          <PaesQuestionCard
            question={paesActiveQuestion}
            selectedOption={paesSelectedOption}
            onSelectOption={selectPaesOption}
            confidence={paesConfidence}
            onChangeConfidence={setPaesConfidence}
            onSubmit={() => submitPaesAttempt(25)}
            lastResult={paesLastResult}
            onNext={nextPaesQuestion}
            loading={paesLoading}
          />

          <SocraticTutorDrawer
            hints={paesSocraticHints}
            onRequestHint={requestSocraticHint}
            loading={paesLoading}
          />
        </div>
      ) : paesSessionId && !paesActiveQuestion ? (
        /* REGULAR BLOCK COMPLETE */
        <div className="card text-center max-w-xl mx-auto my-8 space-y-4 py-8">
          <div className="w-14 h-14 rounded-xl bg-emerald-500/15 text-emerald-400 flex items-center justify-center mx-auto border border-emerald-500/25">
            <icons.trophy size={26} strokeWidth={1.8} />
          </div>
          <h2 className="text-lg font-semibold text-white">Bloque completado</h2>
          <p className="text-sm text-neutral-400 leading-relaxed">
            Tus respuestas quedaron registradas. La estabilidad de memoria y tus errores ya están actualizados.
          </p>
          <button
            onClick={() => {
              resetPaesSession()
              fetchPaesFsrsStatus(1, paesActiveSubject || "M1")
            }}
            className="btn btn-primary"
          >
            Volver a PAES
          </button>
        </div>
      ) : (
        /* SPECIALIZED HUB TABS */
        <div className="space-y-6">
          {/* Barra de Rutina Semanal con Boton 1-Clic (Arriba arriba de los tabs) */}
          <PaesWeeklyRoutineBar
            onStartSession={(subjectCode, count) => {
              if (setPaesActiveSubject) setPaesActiveSubject(subjectCode)
              startPaesSession("PRACTICE", null, count || 15, subjectCode)
            }}
            isStarting={paesLoading}
          />

          {/* Main Tab Navigation: every hub block must be reachable from here */}
          <div className="flex items-center gap-1.5 p-1.5 bg-[#101010] border border-white/[0.07] rounded-xl overflow-x-auto">
            {[
              { id: "exams", label: "Entrenar", icon: "focus" },
              {
                id: "error_vault",
                label: "Errores",
                icon: "error",
                badge: paesErrorNotebook?.total_errors > 0 ? paesErrorNotebook.total_errors : null
              },
              { id: "cruch", label: "Admisión", icon: "analysis" },
              { id: "curriculum", label: `Temario (${paesSubtopicsList.length})`, icon: "curriculum" },
              { id: "parametric", label: "Generador", icon: "parametric" },
              { id: "fsrs", label: "Memoria", icon: "memory" },
            ].map((tab) => {
              const TabIcon = icons[tab.icon]
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`px-3 py-2.5 rounded-lg text-xs font-semibold transition-colors whitespace-nowrap cursor-pointer flex items-center gap-2 ${
                    activeTab === tab.id
                      ? "bg-white text-neutral-950"
                      : "text-neutral-400 hover:text-white hover:bg-white/[0.05]"
                  }`}
                >
                  <TabIcon size={15} strokeWidth={1.8} />
                  <span>{tab.label}</span>
                  {tab.badge ? (
                    <span className={`px-1.5 py-0.5 rounded-full text-[10px] font-mono font-semibold ${
                      activeTab === tab.id
                        ? "bg-rose-500 text-white"
                        : "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                    }`}>
                      {tab.badge}
                    </span>
                  ) : null}
                </button>
              )
            })}
          </div>

          {/* TAB 1: ENTRENAR HOY & SIMULACROS */}
          {activeTab === "exams" && (
            <div className="space-y-6 animate-fade-in">
              {/* Hero Banner */}
              <div className="p-6 rounded-3xl bg-neutral-900/40 border border-white/[0.06] flex flex-col md:flex-row items-center justify-between gap-6">
                <div className="space-y-1 text-center md:text-left">
                  <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-sky-400">
                    Ambiente Oficial DEMRE {currentSubject.code}
                  </span>
                  <h3 className="text-xl font-bold text-white">
                    Simulacros Oficiales de {currentSubject.name}
                  </h3>
                  <p className="text-xs text-neutral-400 max-w-xl">
                    Practica bajo presión real de tiempo ({currentSubject.timePerQ}). Al finalizar, obtienes tu puntaje en escala DEMRE 100–1000 y el solucionario analítico.
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <div className="px-4 py-3 rounded-2xl bg-neutral-950/80 border border-white/[0.06] text-center font-mono">
                    <span className="text-[10px] text-neutral-400 block uppercase">Ritmo Oficial</span>
                    <span className="text-sm font-bold text-sky-400">{currentSubject.timePerQ}</span>
                  </div>
                </div>
              </div>

              {/* 3 Exam Tier Cards */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Mini-Ensayo */}
                <div className="card flex flex-col justify-between">
                  <div className="space-y-3">
                    <div className="flex justify-between items-start">
                      <span className="w-10 h-10 rounded-lg bg-sky-500/10 text-sky-400 flex items-center justify-center">
                        <icons.focus size={19} strokeWidth={1.8} />
                      </span>
                      <span className="badge badge-neutral">{currentExamConfig.mini.time} MIN</span>
                    </div>
                    <div>
                      <h4 className="text-base font-semibold text-white">Mini-ensayo</h4>
                      <p className="text-sm text-neutral-400 mt-1">{currentExamConfig.mini.label}</p>
                    </div>
                    <div className="pt-3 border-t border-white/[0.06] text-xs text-neutral-400">
                      {currentExamConfig.mini.count} preguntas
                    </div>
                  </div>

                  <button
                    onClick={() => startPaesExam(currentExamConfig.mini.count, currentSubject.code)}
                    className="btn btn-secondary w-full mt-5"
                  >
                    Empezar mini-ensayo
                  </button>
                </div>

                {/* Medio Ensayo */}
                <div className="card flex flex-col justify-between">
                  <div className="space-y-3">
                    <div className="flex justify-between items-start">
                      <span className="w-10 h-10 rounded-lg bg-purple-500/10 text-purple-400 flex items-center justify-center">
                        <icons.exam size={19} strokeWidth={1.8} />
                      </span>
                      <span className="badge badge-neutral">{currentExamConfig.mid.time} MIN</span>
                    </div>
                    <div>
                      <h4 className="text-base font-semibold text-white">Ensayo medio</h4>
                      <p className="text-sm text-neutral-400 mt-1">{currentExamConfig.mid.label}</p>
                    </div>
                    <div className="pt-3 border-t border-white/[0.06] text-xs text-neutral-400">
                      {currentExamConfig.mid.count} preguntas
                    </div>
                  </div>

                  <button
                    onClick={() => startPaesExam(currentExamConfig.mid.count, currentSubject.code)}
                    className="btn btn-secondary w-full mt-5"
                  >
                    Empezar ensayo medio
                  </button>
                </div>

                {/* Ensayo Completo DEMRE */}
                <div className="card flex flex-col justify-between border-green-500/25">
                  <div className="space-y-3">
                    <div className="flex justify-between items-start">
                      <span className="w-10 h-10 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center">
                        <icons.paes size={19} strokeWidth={1.8} />
                      </span>
                      <span className="badge badge-deliberate">{currentExamConfig.full.time} MIN</span>
                    </div>
                    <div>
                      <h4 className="text-base font-semibold text-white">Simulacro completo</h4>
                      <p className="text-sm text-neutral-400 mt-1">{currentExamConfig.full.label}</p>
                    </div>
                    <div className="pt-3 border-t border-white/[0.06] text-xs text-neutral-400">
                      {currentExamConfig.full.count} preguntas oficiales DEMRE 2026
                    </div>
                  </div>

                  <button
                    onClick={() => startPaesExam(currentExamConfig.full.count, currentSubject.code)}
                    className="btn btn-primary w-full mt-5"
                  >
                    Empezar simulacro
                    <icons.next size={16} strokeWidth={2} />
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: TEMARIO OFICIAL (13 SUBTEMAS POR EJE) */}
          {activeTab === "curriculum" && (
            <div className="space-y-6 animate-fade-in">
              {Object.entries(subtopicsByEje).map(([ejeName, subtopics]) => (
                <div
                  key={ejeName}
                  className="p-6 rounded-3xl bg-neutral-900/60 border border-white/[0.06] space-y-4"
                >
                  <div className="flex items-center justify-between pb-3 border-b border-white/[0.04]">
                    <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-sky-400" />
                      <span>{ejeName}</span>
                    </h3>
                    <span className="text-xs text-neutral-400 font-mono">
                      {subtopics.length} subtemas
                    </span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {subtopics.map((st) => (
                      <div
                        key={st.id}
                        className="p-4 rounded-2xl bg-neutral-950/60 border border-white/[0.04] hover:border-white/[0.1] transition-all flex items-center justify-between gap-3"
                      >
                        <div className="flex-1 min-w-0">
                          <h4 className="text-xs font-bold text-white truncate">{st.name}</h4>
                          <div className="flex items-center gap-3 mt-1.5 text-[11px] text-neutral-400">
                            <span>
                              Dominio: <strong className="text-sky-400">{Math.round(st.mastery * 100)}%</strong>
                            </span>
                            <span>
                              Caja: <strong className="text-amber-400">{st.leitner_box}</strong>
                            </span>
                          </div>
                          <div className="w-full bg-neutral-800 h-1.5 rounded-full overflow-hidden mt-2">
                            <div
                              className="bg-sky-500 h-full rounded-full transition-all duration-500"
                              style={{ width: `${Math.round(st.mastery * 100)}%` }}
                            />
                          </div>
                        </div>

                        <button
                          onClick={() => handleStartSubtopic(st.slug)}
                          className="px-3.5 py-2 bg-neutral-800 hover:bg-sky-500 hover:text-neutral-950 text-neutral-200 text-xs font-bold rounded-xl border border-white/[0.08] transition-all shrink-0 cursor-pointer"
                        >
                          Entrenar
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* TAB 3: GENERADOR PARAMETRICO SYMPY */}
          {activeTab === "parametric" && (
            <div className="p-6 md:p-8 rounded-3xl bg-neutral-900/60 border border-white/[0.08] space-y-6 animate-fade-in">
              <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pb-6 border-b border-white/[0.06]">
                <div>
                  <span className="text-[10px] font-mono uppercase font-semibold text-purple-400 tracking-wider">
                    Práctica ilimitada
                  </span>
                  <h3 className="text-lg font-semibold text-white">
                    Generador de ejercicios
                  </h3>
                  <p className="text-xs text-neutral-400 mt-0.5">
                    Variantes algebraicas con distractores controlados.
                  </p>
                </div>

                <div className="flex items-center gap-3 flex-wrap">
                  <select
                    value={parametricTemplate}
                    onChange={(e) => {
                      setParametricTemplate(e.target.value)
                      handleGenerateParametric(e.target.value)
                    }}
                    className="input text-xs font-medium cursor-pointer max-w-full"
                  >
                    <option value="PARAM-M1-ALG-01">Ecuación lineal de primer grado</option>
                    <option value="PARAM-M1-ALG-02">Sistema de ecuaciones 2×2</option>
                    <option value="PARAM-M1-GEO-01">Teorema de Pitágoras</option>
                  </select>

                  <button
                    onClick={() => handleGenerateParametric()}
                    disabled={parametricLoading}
                    className="btn btn-primary btn-sm"
                  >
                    <icons.retry size={15} strokeWidth={1.8} />
                    {parametricLoading ? "Generando..." : "Nueva variante"}
                  </button>
                </div>
              </div>

              {parametricQuestion ? (
                <div className="space-y-6">
                  {/* Stem */}
                  <div className="p-5 rounded-2xl bg-neutral-950/80 border border-white/[0.06] text-sm md:text-base text-neutral-100 leading-relaxed font-medium">
                    <MathRenderer text={parametricQuestion.stem} />
                  </div>

                  {/* Options */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {parametricQuestion.options.map((opt) => {
                      const optKey = opt.id || opt.key
                      const isSelected = parametricSelected === optKey
                      const isCorrect = opt.is_correct

                      let borderBgClass = "bg-neutral-950/60 border-white/[0.08] hover:border-white/[0.2] text-neutral-200"
                      if (parametricEvaluated || parametricRevealed) {
                        if (isCorrect) {
                          borderBgClass = "bg-emerald-500/15 border-emerald-500 text-emerald-300 shadow-sm shadow-emerald-500/20"
                        } else if (isSelected) {
                          borderBgClass = "bg-rose-500/15 border-rose-500 text-rose-300"
                        } else {
                          borderBgClass = "bg-neutral-950/40 border-white/[0.04] text-neutral-400 opacity-60"
                        }
                      } else if (isSelected) {
                        borderBgClass = "bg-purple-500/15 border-purple-500 text-purple-200 ring-2 ring-purple-500/30"
                      }

                      return (
                        <button
                          key={optKey}
                          type="button"
                          disabled={parametricEvaluated || parametricRevealed}
                          onClick={() => setParametricSelected(optKey)}
                          className={`p-4 rounded-2xl border transition-all text-left flex items-center gap-3.5 cursor-pointer disabled:cursor-default ${borderBgClass}`}
                        >
                          <span className={`w-8 h-8 rounded-xl flex items-center justify-center font-bold text-xs font-mono shrink-0 transition-colors ${
                            (parametricEvaluated || parametricRevealed) && isCorrect
                              ? "bg-emerald-500 text-neutral-950"
                              : (parametricEvaluated || parametricRevealed) && isSelected
                                ? "bg-rose-500 text-white"
                                : isSelected
                                  ? "bg-purple-500 text-white"
                                  : "bg-neutral-800 text-neutral-400"
                          }`}>
                            {optKey}
                          </span>
                          <div className="flex-1 min-w-0">
                            <MathRenderer text={opt.content || opt.text} />
                          </div>
                          {(parametricEvaluated || parametricRevealed) && isCorrect && (
                            <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-md border border-emerald-500/20">
                              <icons.check size={13} strokeWidth={2.2} />
                              Correcta
                            </span>
                          )}
                          {(parametricEvaluated || parametricRevealed) && isSelected && !isCorrect && (
                            <span className="inline-flex items-center gap-1 text-xs font-medium text-rose-400 bg-rose-500/10 px-2 py-0.5 rounded-md border border-rose-500/20">
                              <icons.close size={13} strokeWidth={2.2} />
                              Tu elección
                            </span>
                          )}
                          {(parametricEvaluated || parametricRevealed) && opt.distractor_type && (
                            <span className="text-[10px] font-mono text-neutral-400 bg-neutral-800/80 px-1.5 py-0.5 rounded border border-white/[0.06]">
                              {opt.distractor_type}
                            </span>
                          )}
                        </button>
                      )
                    })}
                  </div>

                  {/* Actions bar */}
                  <div className="flex items-center justify-between pt-2 border-t border-white/[0.06] flex-wrap gap-3">
                    <div className="flex items-center gap-3">
                      {!parametricEvaluated && !parametricRevealed ? (
                        <button
                          type="button"
                          disabled={!parametricSelected}
                          onClick={() => {
                            setParametricEvaluated(true)
                            setParametricRevealed(true)
                          }}
                          className="btn btn-primary btn-sm"
                        >
                          Comprobar respuesta
                        </button>
                      ) : (
                        <button
                          type="button"
                          onClick={() => handleGenerateParametric()}
                          className="btn btn-secondary btn-sm"
                        >
                          <icons.next size={15} strokeWidth={1.8} />
                          Siguiente ejercicio
                        </button>
                      )}

                      <button
                        type="button"
                        onClick={() => setParametricRevealed(!parametricRevealed)}
                        className="text-xs font-bold text-neutral-400 hover:text-white underline cursor-pointer"
                      >
                        {parametricRevealed ? "Ocultar Solución" : "Revelar Explicación Directa"}
                      </button>
                    </div>

                    {parametricEvaluated && (
                      <div className="text-xs font-mono font-bold">
                        {parametricQuestion.options.find(o => (o.id || o.key) === parametricSelected)?.is_correct ? (
                          <span className="inline-flex items-center gap-1.5 text-emerald-400 bg-emerald-500/10 px-3 py-1.5 rounded-xl border border-emerald-500/20">
                            <icons.success size={14} strokeWidth={2} />
                            Respuesta correcta
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1.5 text-rose-400 bg-rose-500/10 px-3 py-1.5 rounded-xl border border-rose-500/20">
                            <icons.info size={14} strokeWidth={2} />
                            Revisa la solución paso a paso
                          </span>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Complete, Unambiguous Step-by-Step Explanation */}
                  {parametricRevealed && parametricQuestion.explanation && (
                    <div className="p-6 rounded-2xl bg-neutral-950/80 border border-purple-500/30 text-xs text-neutral-300 leading-relaxed space-y-4 animate-fade-in shadow-xl shadow-purple-950/20">
                      <div className="flex items-center gap-2 text-purple-400 font-semibold text-sm border-b border-white/[0.06] pb-2">
                        <icons.exam size={15} strokeWidth={1.8} />
                        <span>Solución paso a paso</span>
                      </div>

                      {/* Step by step */}
                      {parametricQuestion.explanation.step_by_step && (
                        <div className="space-y-1.5">
                          <strong className="text-white block font-bold text-xs">
                            Paso a paso analítico:
                          </strong>
                          <div className="p-3.5 bg-neutral-900/90 rounded-xl border border-white/[0.06] text-neutral-200">
                            <MathRenderer text={parametricQuestion.explanation.step_by_step} />
                          </div>
                        </div>
                      )}

                      {/* Key concept */}
                      {parametricQuestion.explanation.key_concept && (
                        <div className="space-y-1">
                          <strong className="text-sky-400 flex items-center gap-1.5 font-semibold text-xs">
                            <icons.focus size={13} strokeWidth={2} />
                            Concepto clave
                          </strong>
                          <p className="text-neutral-300 pl-1">
                            {parametricQuestion.explanation.key_concept}
                          </p>
                        </div>
                      )}

                      {/* Frequent mistake */}
                      {parametricQuestion.explanation.frequent_mistake && (
                        <div className="space-y-1">
                          <strong className="text-amber-400 flex items-center gap-1.5 font-semibold text-xs">
                            <icons.error size={13} strokeWidth={2} />
                            Error frecuente
                          </strong>
                          <p className="text-neutral-400 pl-1">
                            {parametricQuestion.explanation.frequent_mistake}
                          </p>
                        </div>
                      )}

                      {/* Short summary */}
                      {parametricQuestion.explanation.short_summary && (
                        <div className="pt-2 border-t border-white/[0.04] text-[11px] text-neutral-400 font-mono">
                          Conclusión: <span className="text-white">{parametricQuestion.explanation.short_summary}</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-12 text-neutral-500 text-xs">
                  Haz clic en &quot;Nueva Instancia&quot; para probar el motor algebraico SymPy.
                </div>
              )}
            </div>
          )}

          {/* TAB 4: ERROR VAULT (CUADERNO DE ERRORES) */}
          {activeTab === "error_vault" && (
            <div className="space-y-6 animate-fade-in">
              <PaesErrorVault
                onStartRevenge={(count) => startRevengeSession(count, paesActiveSubject)}
              />
            </div>
          )}

          {/* TAB 5: FSRS RETENTION WIDGET */}
          {activeTab === "fsrs" && (
            <div className="space-y-6 animate-fade-in">
              <FsrsStatusWidget
                fsrsStatus={paesFsrsStatus}
                onReviewDueClick={handleStartGeneral}
                onReviewSubtopic={handleStartSubtopic}
              />
            </div>
          )}

          {/* TAB 6: CRUCH ADMISSION & PROBABILITY SIMULATOR */}
          {activeTab === "cruch" && (
            <div className="space-y-6 animate-fade-in">
              <CruchAdmissionSimulator />
            </div>
          )}
        </div>
      )}
    </div>
  )
}
