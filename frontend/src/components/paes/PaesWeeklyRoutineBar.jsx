import React, { useState, useEffect, useCallback } from "react"
import { api } from "../../api/client"
import { icons } from "../ui/icons"

const CalendarIcon = ({ className = "w-4 h-4" }) => <icons.calendar className={className} />
const PlayIcon = ({ className = "w-4 h-4" }) => <icons.play className={className} />
const SparklesIcon = ({ className = "w-4 h-4" }) => <icons.sparkles className={className} />
const ChevronUpIcon = ({ className = "w-4 h-4" }) => <icons.chevronUp className={className} />
const ChevronDownIcon = ({ className = "w-4 h-4" }) => <icons.chevronDown className={className} />
const CloseIcon = ({ className = "w-4 h-4" }) => <icons.close className={className} />

const DAYS = [
  { key: "monday", label: "Lunes", short: "Lun" },
  { key: "tuesday", label: "Martes", short: "Mar" },
  { key: "wednesday", label: "Miércoles", short: "Mié" },
  { key: "thursday", label: "Jueves", short: "Jue" },
  { key: "friday", label: "Viernes", short: "Vie" },
  { key: "saturday", label: "Sábado", short: "Sáb" },
  { key: "sunday", label: "Domingo", short: "Dom" },
]

const SUBJECT_OPTIONS = [
  { code: "M1", label: "M1 Matemática", color: "from-blue-600 to-indigo-600", badge: "bg-blue-500/20 text-blue-300 border-blue-500/30" },
  { code: "LECTURA", label: "Lectura", color: "from-emerald-600 to-teal-600", badge: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30" },
  { code: "CIENCIAS", label: "Ciencias", color: "from-purple-600 to-violet-600", badge: "bg-purple-500/20 text-purple-300 border-purple-500/30" },
  { code: "M2", label: "M2 Matemática", color: "from-amber-600 to-orange-600", badge: "bg-amber-500/20 text-amber-300 border-amber-500/30" },
  { code: "HISTORIA", label: "Historia", color: "from-rose-600 to-pink-600", badge: "bg-rose-500/20 text-rose-300 border-rose-500/30" },
  { code: "REST", label: "Descanso", color: "from-slate-700 to-slate-800", badge: "bg-slate-500/20 text-slate-400 border-slate-500/30" },
]

const ROUTINE_CACHE_KEY = "peak_paes_weekly_routine"
const COLLAPSED_CACHE_KEY = "peak_paes_routine_collapsed"
const DISMISSED_CACHE_KEY = "peak_paes_routine_dismissed"

const DEFAULT_ROUTINE = {
  monday: "M1",
  tuesday: "LECTURA",
  wednesday: "M1",
  thursday: "CIENCIAS",
  friday: "M1",
  saturday: "M1",
  sunday: "REST",
}

const SAVE_STATUS_LABELS = {
  idle: "Se guarda automáticamente",
  saving: "Guardando…",
  saved: "Guardado",
  error: "Falló el guardado",
}

function readCachedRoutine() {
  try {
    const raw = localStorage.getItem(ROUTINE_CACHE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    return parsed && typeof parsed === "object" ? parsed : null
  } catch (err) {
    console.warn("[PaesWeeklyRoutineBar] Could not read the cached weekly routine", err)
    return null
  }
}

function writeCachedRoutine(routine) {
  try {
    localStorage.setItem(ROUTINE_CACHE_KEY, JSON.stringify(routine))
    return true
  } catch (err) {
    console.warn("[PaesWeeklyRoutineBar] Could not cache the weekly routine locally", err)
    return false
  }
}

export function PaesWeeklyRoutineBar({ onStartSession, isStarting = false, onDismiss = null, todayKey: todayKeyOverride = null }) {
  const [routine, setRoutine] = useState(DEFAULT_ROUTINE)
  const [saveStatus, setSaveStatus] = useState("idle")
  const [saveError, setSaveError] = useState("")
  const [pendingSave, setPendingSave] = useState(null)

  // `todayKeyOverride` lets callers (and tests) pin "today" instead of reading
  // the wall clock, so behaviour never depends on the day the suite runs.
  const todayDayIndex = new Date().getDay()
  const todayKey = todayKeyOverride || DAYS[todayDayIndex === 0 ? 6 : todayDayIndex - 1].key
  const [selectedDay, setSelectedDay] = useState(todayKey)

  const [isCollapsed, setIsCollapsed] = useState(() => {
    try {
      return localStorage.getItem(COLLAPSED_CACHE_KEY) === "true"
    } catch {
      return false
    }
  })
  const [isDismissed, setIsDismissed] = useState(() => {
    try {
      return localStorage.getItem(DISMISSED_CACHE_KEY) === "true"
    } catch {
      return false
    }
  })

  useEffect(() => {
    let isMounted = true
    api.paes.getRoutine()
      .then((res) => {
        if (!isMounted) return
        if (res?.routine) {
          setRoutine(res.routine)
          writeCachedRoutine(res.routine)
        }
      })
      .catch(() => {
        const cached = readCachedRoutine()
        if (cached && isMounted) {
          setRoutine(cached)
        }
      })
    return () => { isMounted = false }
  }, [])

  const persistRoutine = useCallback(async (nextRoutine, previousRoutine) => {
    setSaveStatus("saving")
    setSaveError("")
    try {
      const res = await api.paes.updateRoutine(nextRoutine)
      const acknowledged =
        res && typeof res.routine === "object" && res.routine !== null
          ? res.routine
          : nextRoutine
      setRoutine(acknowledged)
      setPendingSave(null)
      writeCachedRoutine(acknowledged)
      setSaveStatus("saved")
      return true
    } catch (err) {
      console.error("[PaesWeeklyRoutineBar] Could not save the weekly routine", err)
      setRoutine(previousRoutine)
      setPendingSave({ routine: nextRoutine, previous: previousRoutine })
      setSaveError("No se pudo guardar tu rutina semanal.")
      setSaveStatus("error")
      return false
    }
  }, [])

  const handleRetrySave = async () => {
    if (!pendingSave) return
    await persistRoutine(pendingSave.routine, pendingSave.previous)
  }

  const handleToggleCollapse = () => {
    setIsCollapsed((prev) => {
      const next = !prev
      try {
        localStorage.setItem(COLLAPSED_CACHE_KEY, String(next))
      } catch (err) {
        console.warn("Could not save collapse state", err)
      }
      return next
    })
  }

  const handleDismiss = () => {
    setIsDismissed(true)
    try {
      localStorage.setItem(DISMISSED_CACHE_KEY, "true")
    } catch (err) {
      console.warn("Could not save dismissed state", err)
    }
    if (onDismiss) onDismiss()
  }

  const handleRestore = () => {
    setIsDismissed(false)
    try {
      localStorage.setItem(DISMISSED_CACHE_KEY, "false")
    } catch (err) {
      console.warn("Could not save dismissed state", err)
    }
  }

  const handleSelectSubject = (code) => {
    if (saveStatus === "saving") return
    if (routine[selectedDay] === code) return
    const nextRoutine = { ...routine, [selectedDay]: code }
    persistRoutine(nextRoutine, routine)
  }

  const todaySubjectCode = routine[todayKey] || "M1"
  const todayOption = SUBJECT_OPTIONS.find((s) => s.code === todaySubjectCode) || SUBJECT_OPTIONS[0]
  const isRestDay = todaySubjectCode === "REST"
  const selectedDayLabel = DAYS.find((d) => d.key === selectedDay)?.label || "día"

  // Si la barra fue eliminada/ocultada de la pantalla
  if (isDismissed) {
    return (
      <div className="flex items-center justify-between p-3 px-4 mb-6 rounded-2xl bg-slate-900/60 border border-slate-800/80 text-xs text-slate-400 backdrop-blur-sm animate-fade-in">
        <div className="flex items-center gap-2">
          <CalendarIcon className="w-4 h-4 text-indigo-400" />
          <span>Rutina semanal oculta de la pantalla</span>
        </div>
        <button
          type="button"
          onClick={handleRestore}
          className="px-3 py-1 bg-indigo-500/20 hover:bg-indigo-500/30 text-indigo-300 border border-indigo-500/30 rounded-lg text-xs font-semibold transition-colors cursor-pointer"
        >
          Mostrar Rutina
        </button>
      </div>
    )
  }

  // Si la barra está retraída / colapsada
  if (isCollapsed) {
    return (
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl px-5 py-3 mb-6 shadow-xl backdrop-blur-sm relative overflow-hidden flex flex-col sm:flex-row items-center justify-between gap-3 animate-fade-in">
        <div className="absolute -top-24 -right-24 w-72 h-72 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="flex items-center gap-3">
          <div className="p-2 bg-indigo-500/10 border border-indigo-500/20 rounded-lg text-indigo-400">
            <CalendarIcon className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold text-slate-100">Tu Rutina Semanal</h3>
              <span className="text-[10px] text-slate-500 font-mono">(Retraída)</span>
            </div>
            <div className="text-xs text-slate-400 flex items-center gap-1.5 mt-0.5">
              <span>Hoy {DAYS.find((d) => d.key === todayKey)?.label}:</span>
              <span className={`px-2 py-0.2 rounded text-[10px] font-semibold border ${todayOption.badge}`}>
                {todayOption.label}
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            disabled={isStarting}
            onClick={() => onStartSession(todaySubjectCode === "REST" ? "M1" : todaySubjectCode, 15)}
            className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-white font-semibold text-xs shadow-md transition-all duration-200 hover:brightness-110 active:scale-95 disabled:opacity-50 bg-gradient-to-r ${todayOption.color}`}
          >
            <PlayIcon className="w-3.5 h-3.5 fill-white" />
            <span>{isStarting ? "Cargando..." : `Iniciar (${todayOption.code === "REST" ? "M1" : todayOption.code})`}</span>
          </button>

          <button
            type="button"
            onClick={handleToggleCollapse}
            className="text-xs px-2.5 py-1.5 rounded-lg border border-slate-800 bg-slate-950/60 hover:bg-slate-800 hover:border-slate-700 text-slate-400 hover:text-slate-200 transition-all cursor-pointer flex items-center gap-1"
            title="Desplegar rutina semanal"
            aria-label="Desplegar rutina semanal"
          >
            <ChevronDownIcon className="w-3.5 h-3.5 text-indigo-400" />
            <span className="hidden sm:inline">Desplegar</span>
          </button>

          <button
            type="button"
            onClick={handleDismiss}
            className="text-xs p-1.5 sm:px-2 sm:py-1.5 rounded-lg border border-slate-800 bg-slate-950/60 hover:bg-rose-500/10 hover:border-rose-500/30 text-slate-400 hover:text-rose-300 transition-all cursor-pointer flex items-center gap-1"
            title="Eliminar de la pantalla"
            aria-label="Eliminar rutina de la pantalla"
          >
            <CloseIcon className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Eliminar</span>
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 mb-8 shadow-xl backdrop-blur-sm relative overflow-hidden animate-fade-in">
      <div className="absolute -top-24 -right-24 w-72 h-72 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
        <div className="flex items-center gap-2.5">
          <div className="p-2 bg-indigo-500/10 border border-indigo-500/20 rounded-lg text-indigo-400">
            <CalendarIcon className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-slate-100">Tu Rutina Semanal</h3>
            <p className="text-xs text-slate-400">Toca un día y elige su materia. Se guarda solo.</p>
          </div>
        </div>
        <div className="flex items-center gap-2 self-start sm:self-auto">
          <button
            type="button"
            onClick={handleToggleCollapse}
            className="text-xs px-2.5 py-1.5 rounded-lg border border-slate-800 bg-slate-950/60 hover:bg-slate-800 hover:border-slate-700 text-slate-400 hover:text-slate-200 transition-all cursor-pointer flex items-center gap-1 shadow-sm"
            title="Retraer rutina semanal"
            aria-label="Retraer rutina semanal"
          >
            <ChevronUpIcon className="w-3.5 h-3.5 text-indigo-400" />
            <span className="hidden sm:inline">Retraer</span>
          </button>
          <button
            type="button"
            onClick={handleDismiss}
            className="text-xs p-1.5 sm:px-2.5 sm:py-1.5 rounded-lg border border-slate-800 bg-slate-950/60 hover:bg-rose-500/10 hover:border-rose-500/30 text-slate-400 hover:text-rose-300 transition-all cursor-pointer flex items-center gap-1 shadow-sm"
            title="Eliminar de la pantalla"
            aria-label="Eliminar rutina de la pantalla"
          >
            <CloseIcon className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Eliminar</span>
          </button>
        </div>
      </div>

      <div className="grid grid-cols-4 md:grid-cols-7 gap-2 sm:gap-2.5 mb-4">
        {DAYS.map((day) => {
          const isToday = day.key === todayKey
          const isSelected = day.key === selectedDay
          const subjCode = routine[day.key] || "M1"
          const subjConfig = SUBJECT_OPTIONS.find((s) => s.code === subjCode) || SUBJECT_OPTIONS[0]
          return (
            <button
              key={day.key}
              type="button"
              onClick={() => setSelectedDay(day.key)}
              aria-pressed={isSelected}
              className={`w-full flex flex-col items-center justify-between gap-1.5 p-3 rounded-xl border transition-all min-h-[96px] md:min-h-[84px] cursor-pointer ${
                isSelected
                  ? "bg-slate-800/90 border-indigo-500 shadow-md shadow-indigo-500/10 ring-1 ring-indigo-500/40"
                  : "bg-slate-950/60 border-slate-800 hover:border-slate-700 hover:bg-slate-800/40"
              }`}
            >
              <div className="flex items-center justify-between w-full">
                <span className={`text-xs font-semibold ${isSelected ? "text-indigo-300 font-bold" : "text-slate-400"}`}>{day.short}</span>
                {isToday && <span className="text-[9px] uppercase tracking-wider font-extrabold px-1 rounded bg-indigo-500 text-white leading-none py-0.5">Hoy</span>}
              </div>
              <span className={`w-full text-center px-2 py-1 rounded-md text-xs font-semibold border ${subjConfig.badge} truncate`}>
                {subjConfig.code === "REST" ? "Libre" : subjConfig.code}
              </span>
              <span className="text-[10px] text-slate-500 truncate w-full text-center">{subjConfig.label}</span>
            </button>
          )
        })}
      </div>

      <div className="mb-4 rounded-xl border border-slate-800 bg-slate-950/50 p-3">
        <div className="flex items-center justify-between gap-2 mb-2">
          <p className="text-xs font-semibold text-slate-200">Materia del {selectedDayLabel.toLowerCase()}</p>
          <span
            data-testid="routine-save-status"
            className={`text-[11px] ${saveStatus === "error" ? "text-rose-300" : saveStatus === "saved" ? "text-emerald-300" : saveStatus === "saving" ? "text-sky-300" : "text-slate-500"}`}
          >
            {SAVE_STATUS_LABELS[saveStatus]}
          </span>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {SUBJECT_OPTIONS.map((opt) => {
            const isSelected = (routine[selectedDay] || "M1") === opt.code
            return (
              <button
                key={opt.code}
                type="button"
                data-testid={`subject-chip-${opt.code}`}
                onClick={() => handleSelectSubject(opt.code)}
                disabled={saveStatus === "saving"}
                className={`px-2.5 py-1 rounded-lg text-xs font-medium border transition-all disabled:opacity-50 cursor-pointer ${
                  isSelected
                    ? `${opt.badge} ring-1 ring-indigo-400/50 font-bold scale-[1.02]`
                    : "border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700"
                }`}
              >
                {opt.code === "REST" ? "Libre" : opt.code}
              </button>
            )
          })}
        </div>
      </div>

      {saveStatus === "error" && (
        <div role="alert" className="mb-4 flex flex-col sm:flex-row sm:items-center gap-3 rounded-xl border border-rose-500/40 bg-rose-500/10 px-4 py-3">
          <p className="text-xs text-rose-100 flex-1">{saveError}</p>
          {pendingSave && (
            <button
              type="button"
              onClick={handleRetrySave}
              className="shrink-0 self-start rounded-lg border border-rose-400/40 bg-rose-500/20 px-3 py-1.5 text-xs font-bold text-rose-100 transition-colors hover:bg-rose-500/30 cursor-pointer"
            >
              Reintentar
            </button>
          )}
        </div>
      )}

      {saveStatus === "saved" && (
        <p role="status" className="mb-4 text-xs text-emerald-300">
          Rutina guardada.
        </p>
      )}
    </div>
  )
}
