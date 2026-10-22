import React, { useState, useEffect, useCallback } from "react"
import { api } from "../../api/client"

// Iconos SVG nativos ultralivianos (Cero dependencias externas npm)
function CalendarIcon({ className = "w-4 h-4" }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
    </svg>
  )
}

function PlayIcon({ className = "w-4 h-4" }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M8 5v14l11-7z" />
    </svg>
  )
}

function SparklesIcon({ className = "w-4 h-4" }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
    </svg>
  )
}

function CheckIcon({ className = "w-4 h-4" }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
    </svg>
  )
}

function CoffeeIcon({ className = "w-4 h-4" }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 8h1a4 4 0 010 8h-1M2 8h16v9a4 4 0 01-4 4H6a4 4 0 01-4-4V8zM6 1v3M10 1v3M14 1v3" />
    </svg>
  )
}

function BookIcon({ className = "w-4 h-4" }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
    </svg>
  )
}

function GearIcon({ className = "w-4 h-4" }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
  )
}

function ChevronUpIcon({ className = "w-4 h-4" }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
    </svg>
  )
}

function ChevronDownIcon({ className = "w-4 h-4" }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
    </svg>
  )
}

function CloseIcon({ className = "w-4 h-4" }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
    </svg>
  )
}

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

const ROUTINE_PRESETS = [
  {
    id: "ubb",
    name: "Enfoque M1 UBB (Recomendado)",
    desc: "4 días M1, 1 Lectura, 1 Ciencias y Domingo libre. Óptimo para Ing. en Automatización UBB.",
    routine: {
      monday: "M1",
      tuesday: "LECTURA",
      wednesday: "M1",
      thursday: "CIENCIAS",
      friday: "M1",
      saturday: "M1",
      sunday: "REST",
    },
  },
  {
    id: "math_pro",
    name: "Full Matemáticas (M1 + M2)",
    desc: "Refuerzo intensivo para asegurar puntaje máximo en M1 y M2.",
    routine: {
      monday: "M1",
      tuesday: "M2",
      wednesday: "M1",
      thursday: "M2",
      friday: "M1",
      saturday: "CIENCIAS",
      sunday: "REST",
    },
  },
  {
    id: "balanced",
    name: "Equilibrado PAES",
    desc: "Distribución uniforme para todas las pruebas.",
    routine: {
      monday: "M1",
      tuesday: "LECTURA",
      wednesday: "CIENCIAS",
      thursday: "M1",
      friday: "M2",
      saturday: "HISTORIA",
      sunday: "REST",
    },
  },
  {
    id: "weekend_off",
    name: "Fin de Semana Libre",
    desc: "Carga de lunes a viernes con descanso total sábado y domingo.",
    routine: {
      monday: "M1",
      tuesday: "LECTURA",
      wednesday: "M1",
      thursday: "CIENCIAS",
      friday: "M1",
      saturday: "REST",
      sunday: "REST",
    },
  },
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
  idle: "Customizable",
  saving: "Saving…",
  saved: "Saved",
  error: "Save failed",
}

const SAVE_STATUS_STYLES = {
  idle: "bg-slate-800 text-slate-300 border-slate-700/60 hover:bg-slate-700/80 hover:text-white",
  saving: "bg-sky-500/10 text-sky-300 border-sky-500/30",
  saved: "bg-emerald-500/10 text-emerald-300 border-emerald-500/30",
  error: "bg-rose-500/10 text-rose-300 border-rose-500/30",
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
  const [activeDayPicker, setActiveDayPicker] = useState(null)
  const [saveStatus, setSaveStatus] = useState("idle")
  const [saveError, setSaveError] = useState("")
  const [pendingSave, setPendingSave] = useState(null)

  // Estados de interfaz: Modal Personalizador, Retraído y Eliminado/Oculto
  const [isCustomizerOpen, setIsCustomizerOpen] = useState(false)
  const [tempRoutine, setTempRoutine] = useState(DEFAULT_ROUTINE)
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

  // Determinar qué día es hoy (0 = Sunday, 1 = Monday...)
  // `todayKeyOverride` lets callers (and tests) pin "today" instead of reading
  // the wall clock, so behaviour never depends on the day the suite runs.
  const todayDayIndex = new Date().getDay()
  const todayKey = todayKeyOverride || DAYS[todayDayIndex === 0 ? 6 : todayDayIndex - 1].key

  useEffect(() => {
    let isMounted = true
    api.paes.getRoutine(1)
      .then((res) => {
        if (!isMounted) return
        if (res?.routine) {
          setRoutine(res.routine)
          setTempRoutine(res.routine)
          writeCachedRoutine(res.routine)
        }
      })
      .catch(() => {
        const cached = readCachedRoutine()
        if (cached && isMounted) {
          setRoutine(cached)
          setTempRoutine(cached)
        }
      })
    return () => { isMounted = false }
  }, [])

  const persistRoutine = useCallback(async (nextRoutine, previousRoutine) => {
    setSaveStatus("saving")
    setSaveError("")
    try {
      const res = await api.paes.updateRoutine(nextRoutine, 1)
      const acknowledged =
        res && typeof res.routine === "object" && res.routine !== null
          ? res.routine
          : nextRoutine
      setRoutine(acknowledged)
      setTempRoutine(acknowledged)
      setPendingSave(null)
      writeCachedRoutine(acknowledged)
      setSaveStatus("saved")
      return true
    } catch (err) {
      console.error("[PaesWeeklyRoutineBar] Could not save the weekly routine", err)
      setRoutine(previousRoutine)
      setTempRoutine(previousRoutine)
      setPendingSave({ routine: nextRoutine, previous: previousRoutine })
      setSaveError(
        "Your weekly routine could not be saved, so this change was not saved."
      )
      setSaveStatus("error")
      return false
    }
  }, [])

  const handleSelectSubject = async (dayKey, subjectCode) => {
    const previous = routine
    const updated = { ...previous, [dayKey]: subjectCode }
    setRoutine(updated)
    setTempRoutine(updated)
    setActiveDayPicker(null)
    await persistRoutine(updated, previous)
  }

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

  const handleOpenCustomizer = () => {
    setTempRoutine({ ...routine })
    setIsCustomizerOpen(true)
  }

  const handleApplyPreset = (presetRoutine) => {
    setTempRoutine({ ...presetRoutine })
  }

  const handleSaveCustomizer = async () => {
    setIsCustomizerOpen(false)
    await persistRoutine(tempRoutine, routine)
  }

  const todaySubjectCode = routine[todayKey] || "M1"
  const todayOption = SUBJECT_OPTIONS.find((s) => s.code === todaySubjectCode) || SUBJECT_OPTIONS[0]
  const isRestDay = todaySubjectCode === "REST"

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
            onClick={handleOpenCustomizer}
            data-testid="routine-save-status"
            className={`text-xs px-2.5 py-1.5 rounded-lg border font-medium flex items-center gap-1.5 transition-all cursor-pointer ${SAVE_STATUS_STYLES[saveStatus]}`}
            title="Personalizar rutina semanal"
            aria-label="Personalizar rutina semanal"
          >
            <GearIcon className="w-3.5 h-3.5 text-indigo-400" />
            <span>{SAVE_STATUS_LABELS[saveStatus]}</span>
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

        {/* Modal de personalización incluso si está retraído */}
        {isCustomizerOpen && renderCustomizerModal()}
      </div>
    )
  }

  // Función de renderizado del Modal de Personalización
  function renderCustomizerModal() {
    return (
      <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in duration-200">
        <div className="bg-slate-900 border border-slate-800 rounded-3xl max-w-2xl w-full p-6 shadow-2xl space-y-6 relative max-h-[90vh] overflow-y-auto">
          {/* Header del Modal */}
          <div className="flex items-center justify-between border-b border-slate-800 pb-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-indigo-500/10 border border-indigo-500/20 rounded-xl text-indigo-400">
                <GearIcon className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-white">Personalizar Rutina Semanal</h2>
                <p className="text-xs text-slate-400">
                  Ajusta la materia de cada día o aplica una plantilla de estudio recomendada.
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setIsCustomizerOpen(false)}
              className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
              aria-label="Cerrar modal"
            >
              <CloseIcon className="w-5 h-5" />
            </button>
          </div>

          {/* Plantillas Recomendadas (Presets) */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
              Plantillas Rápidas (1-Clic)
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {ROUTINE_PRESETS.map((preset) => (
                <button
                  key={preset.id}
                  type="button"
                  onClick={() => handleApplyPreset(preset.routine)}
                  className="p-3 text-left rounded-xl border border-slate-800 bg-slate-950/60 hover:border-indigo-500/50 hover:bg-indigo-500/5 transition-all group"
                >
                  <div className="text-xs font-bold text-slate-200 group-hover:text-indigo-300">
                    {preset.name}
                  </div>
                  <div className="text-[11px] text-slate-400 mt-1 leading-snug">
                    {preset.desc}
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Asignación Día por Día */}
          <div className="space-y-3">
            <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
              Configuración por Día
            </label>
            <div className="space-y-2">
              {DAYS.map((day) => {
                const currentCode = tempRoutine[day.key] || "M1"
                return (
                  <div
                    key={day.key}
                    className="flex flex-col sm:flex-row sm:items-center justify-between p-2.5 rounded-xl border border-slate-800/80 bg-slate-950/40 gap-2"
                  >
                    <span className="text-xs font-semibold text-slate-200 w-24">
                      {day.label}
                    </span>
                    <div className="flex flex-wrap items-center gap-1.5 flex-1 justify-start sm:justify-end">
                      {SUBJECT_OPTIONS.map((opt) => {
                        const isSelected = currentCode === opt.code
                        return (
                          <button
                            key={opt.code}
                            type="button"
                            onClick={() => setTempRoutine((prev) => ({ ...prev, [day.key]: opt.code }))}
                            className={`px-2.5 py-1 rounded-lg text-xs font-medium border transition-all ${
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
                )
              })}
            </div>
          </div>

          {/* Acciones del Modal */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-800">
            <button
              type="button"
              onClick={() => setIsCustomizerOpen(false)}
              className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-white rounded-xl transition-colors"
            >
              Cancelar
            </button>
            <button
              type="button"
              onClick={handleSaveCustomizer}
              className="px-5 py-2.5 text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-500 rounded-xl shadow-lg shadow-indigo-600/30 transition-all cursor-pointer"
            >
              Guardar Rutina
            </button>
          </div>
        </div>
      </div>
    )
  }

  // Vista Expandida Principal
  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 mb-8 shadow-xl backdrop-blur-sm relative overflow-hidden animate-fade-in">
      {/* Background glow sutil */}
      <div className="absolute -top-24 -right-24 w-72 h-72 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />

      {/* Header del Calendario de Rutina con Opciones Arriba Arriba */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
        <div className="flex items-center gap-2.5">
          <div className="p-2 bg-indigo-500/10 border border-indigo-500/20 rounded-lg text-indigo-400">
            <CalendarIcon className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-slate-100 flex items-center gap-2">
              Tu Rutina Semanal de 1-Clic
            </h3>
            <p className="text-xs text-slate-400">
              Haz clic en cualquier día para cambiar la materia que te toca automáticamente.
            </p>
          </div>
        </div>

        {/* Barra de Acciones Arriba Arriba: Customizable (Botón) + Retraer + Eliminar */}
        <div className="flex items-center gap-2 self-start sm:self-auto">
          {/* Botón Customizable interactivo */}
          <button
            type="button"
            onClick={handleOpenCustomizer}
            data-testid="routine-save-status"
            className={`text-xs px-2.5 py-1.5 rounded-lg border font-medium flex items-center gap-1.5 transition-all cursor-pointer shadow-sm ${SAVE_STATUS_STYLES[saveStatus]}`}
            title="Haz clic para personalizar tu rutina semanal"
            aria-label="Personalizar rutina semanal"
          >
            <GearIcon className="w-3.5 h-3.5 text-indigo-400" />
            <span>{SAVE_STATUS_LABELS[saveStatus]}</span>
          </button>

          {/* Botón Retraer */}
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

          {/* Botón Eliminar / Ocultar de la pantalla */}
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

      {/* Barra de los 7 días */}
      <div className="grid grid-cols-7 gap-1.5 sm:gap-2 mb-6">
        {DAYS.map((day) => {
          const isToday = day.key === todayKey
          const subjCode = routine[day.key] || "M1"
          const subjConfig = SUBJECT_OPTIONS.find((s) => s.code === subjCode) || SUBJECT_OPTIONS[0]
          const isPickerOpen = activeDayPicker === day.key

          return (
            <div key={day.key} className="relative">
              <button
                type="button"
                onClick={() => setActiveDayPicker(isPickerOpen ? null : day.key)}
                className={`w-full flex flex-col items-center justify-between p-2 sm:p-2.5 rounded-xl border transition-all text-left group cursor-pointer ${
                  isToday
                    ? "bg-slate-800/90 border-indigo-500 shadow-md shadow-indigo-500/10 ring-1 ring-indigo-500/40"
                    : "bg-slate-950/60 border-slate-800 hover:border-slate-700 hover:bg-slate-800/40"
                }`}
              >
                <div className="flex items-center justify-between w-full mb-1.5">
                  <span className={`text-[11px] sm:text-xs font-semibold ${isToday ? "text-indigo-300 font-bold" : "text-slate-400"}`}>
                    {day.short}
                  </span>
                  {isToday && (
                    <span className="text-[9px] uppercase tracking-wider font-extrabold px-1 rounded bg-indigo-500 text-white leading-none py-0.5">
                      Hoy
                    </span>
                  )}
                </div>

                <div className={`w-full text-center py-1 rounded-md text-[11px] sm:text-xs font-medium border ${subjConfig.badge} transition-transform group-hover:scale-[1.02]`}>
                  {subjConfig.code === "REST" ? "Libre" : subjConfig.code}
                </div>
              </button>

              {/* Popover desplegable para elegir materia rápida */}
              {isPickerOpen && (
                <div className="absolute z-30 top-full mt-2 left-1/2 -translate-x-1/2 w-48 bg-slate-900 border border-slate-700 rounded-xl shadow-2xl p-2 space-y-1 animate-in fade-in zoom-in-95 duration-150">
                  <div className="text-[10px] uppercase font-bold text-slate-400 px-2 py-1 border-b border-slate-800 mb-1">
                    Asignar {day.label}
                  </div>
                  {SUBJECT_OPTIONS.map((opt) => (
                    <button
                      key={opt.code}
                      type="button"
                      onClick={() => handleSelectSubject(day.key, opt.code)}
                      className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs transition-colors cursor-pointer ${
                        subjCode === opt.code
                          ? "bg-indigo-600/30 text-indigo-200 border border-indigo-500/30"
                          : "text-slate-300 hover:bg-slate-800 hover:text-white"
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        {opt.code === "REST" ? (
                          <CoffeeIcon className="w-3.5 h-3.5 text-slate-400" />
                        ) : (
                          <BookIcon className="w-3.5 h-3.5 text-indigo-400" />
                        )}
                        <span>{opt.label}</span>
                      </div>
                      {subjCode === opt.code && <CheckIcon className="w-3.5 h-3.5 text-indigo-400" />}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Feedback de guardado */}
      {saveStatus === "error" && (
        <div
          role="alert"
          className="mb-4 flex flex-col sm:flex-row sm:items-center gap-3 rounded-xl border border-rose-500/40 bg-rose-500/10 px-4 py-3"
        >
          <p className="text-xs text-rose-100 flex-1">{saveError}</p>
          {pendingSave && (
            <button
              type="button"
              onClick={handleRetrySave}
              className="shrink-0 self-start rounded-lg border border-rose-400/40 bg-rose-500/20 px-3 py-1.5 text-xs font-bold text-rose-100 transition-colors hover:bg-rose-500/30 cursor-pointer"
            >
              Retry save
            </button>
          )}
        </div>
      )}

      {saveStatus === "saved" && (
        <p role="status" className="mb-4 text-xs text-emerald-300">
          Weekly routine saved.
        </p>
      )}

      {/* Botón Principal de 1-Clic para hoy */}
      <div className="pt-2 border-t border-slate-800/80 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="hidden sm:flex p-2.5 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
            <SparklesIcon className="w-5 h-5" />
          </div>
          <div>
            <div className="text-xs text-slate-400 flex items-center gap-2">
              <span>Módulo del día:</span>
              <span className={`px-2 py-0.5 rounded text-[11px] font-semibold border ${todayOption.badge}`}>
                {todayOption.label}
              </span>
            </div>
            <div className="text-sm font-medium text-slate-200 mt-0.5">
              {isRestDay
                ? "Hoy está configurado como día de descanso. ¡Tú decides si quieres darle igual!"
                : "Dosis diaria recomendada: 15 preguntas calibradas (25 minutos)."}
            </div>
          </div>
        </div>

        <button
          type="button"
          disabled={isStarting}
          onClick={() => onStartSession(todaySubjectCode === "REST" ? "M1" : todaySubjectCode, 15)}
          className={`flex items-center justify-center gap-2.5 px-6 py-3.5 rounded-xl text-white font-semibold text-sm shadow-lg transition-all duration-200 transform hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none bg-gradient-to-r ${todayOption.color} hover:brightness-110 shadow-indigo-500/20 cursor-pointer`}
        >
          <PlayIcon className="w-4 h-4 fill-white" />
          <span>{isStarting ? "Cargando sesión..." : `Iniciar Entrenamiento de Hoy (15 Preguntas)`}</span>
        </button>
      </div>

      {/* Modal de Personalización */}
      {isCustomizerOpen && renderCustomizerModal()}
    </div>
  )
}
