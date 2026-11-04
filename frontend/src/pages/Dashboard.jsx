import { useEffect } from "react"
import { useNavigate } from "react-router"
import { useStore } from "../store/store"
import DeliberatePracticeHero from "../components/dashboard/DeliberatePracticeHero"
import OptimalDailyAction from "../components/dashboard/OptimalDailyAction"
import TeseoBanner from "../components/dashboard/TeseoBanner"
import DualProgressRadar from "../components/dashboard/DualProgressRadar"
import { PaesWeeklyRoutineBar } from "../components/paes/PaesWeeklyRoutineBar"
import Timeline from "../components/Timeline"
import ChallengeList from "../components/ChallengeList"
import { SkeletonHero } from "../components/ui/Skeleton"
import { ErrorBoundary } from "../components/ui/ErrorBoundary"
import { PageTransition } from "../components/ui/PageTransition"
import { icons } from "../components/ui/icons"

export default function Dashboard() {
  const navigate = useNavigate()
  const { summary, timeline, paesSubtopicsList, loading, error, clearError, fetchSkills, fetchSummary, fetchTimeline, fetchChallenges, fetchPaesSubtopics, fetchPaesFsrsStatus, paesActiveSubject, setPaesActiveSubject } = useStore()

  useEffect(() => {
    fetchSkills()
    fetchSummary()
    fetchTimeline()
    fetchChallenges()
    if (fetchPaesSubtopics) fetchPaesSubtopics(null, "ALL")
    if (fetchPaesFsrsStatus) fetchPaesFsrsStatus(null, null)
  }, [paesActiveSubject])

  const isLoading = loading && !timeline?.length

  // Ocultar métricas sin datos: solo mostrar el hero cuando ya hay sesiones
  const hasSessions = (summary?.total_sessions ?? 0) > 0 || (timeline?.length ?? 0) > 0

  // Ocultar proyección DEMRE sin datos: solo mostrarla cuando ya hay intentos
  const hasAttempts = paesSubtopicsList?.some((s) => (s.attempts || 0) > 0) ?? false

  return (
    <PageTransition>
      {/* 1. Barco de Teseo plegable */}
      <TeseoBanner />

      <PaesWeeklyRoutineBar onStartSession={(subject) => { setPaesActiveSubject(subject); navigate(`/paes?subject=${subject}`) }} />

      {/* 2. Acción principal */}
      <OptimalDailyAction />

      {/* 3. Hero de práctica — solo con datos */}
      {isLoading ? <SkeletonHero /> : hasSessions ? <DeliberatePracticeHero /> : null}

      {/* Filas de Teseo y acción eliminadas del inicio por duplicación; la acción principal va arriba */}

      {/* 3. Progreso — solo con datos (sin datos no se muestra 100/1000) */}
      {hasAttempts && <DualProgressRadar />}

      {/* Error Banner if any */}
      {error && (
        <div
          className="mb-8 p-4 bg-red-500/[0.08] border border-red-500/20 rounded-2xl flex items-center justify-between"
          style={{ animation: "fadeInUp 0.3s ease-out" }}
        >
          <div className="flex items-center gap-3">
            <span className="w-8 h-8 rounded-lg bg-red-500/10 flex items-center justify-center text-red-400">
              <icons.close size={16} strokeWidth={2} />
            </span>
            <p className="text-sm text-red-400">
              Error de conexión: {typeof error === "string" ? error : JSON.stringify(error)}
            </p>
          </div>
          <button
            onClick={clearError}
            className="text-xs text-red-500/60 hover:text-red-400 transition-colors"
          >
            Cerrar
          </button>
        </div>
      )}

      {/* Desafíos Activos & Auditoría */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Active AI Challenges */}
        <div className="lg:col-span-5 space-y-6">
          <ErrorBoundary fallbackMessage="Los desafíos no pudieron cargarse.">
            <div className="p-6 rounded-3xl bg-white/[0.02] border border-white/[0.06]">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-9 h-9 rounded-lg bg-purple-500/10 border border-purple-500/20 flex items-center justify-center">
                  <icons.sparkles size={18} strokeWidth={1.8} className="text-purple-400" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white tracking-tight">Desafíos Deliberados</h3>
                  <p className="text-xs text-neutral-400">Micro-metas generadas por IA</p>
                </div>
              </div>
              <ChallengeList />
            </div>
          </ErrorBoundary>
        </div>

        {/* Right Column: Deliberate Practice Audit Timeline */}
        <div className="lg:col-span-7">
          <ErrorBoundary fallbackMessage="El registro de auditoría no pudo cargarse.">
            <div className="p-6 rounded-3xl bg-white/[0.02] border border-white/[0.06]">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-9 h-9 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
                  <icons.exam size={18} strokeWidth={1.8} className="text-emerald-400" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-white tracking-tight">Registro de Auditoría</h3>
                  <p className="text-xs text-neutral-400">Veredictos de práctica deliberada & detección de errores</p>
                </div>
              </div>
              <Timeline />
            </div>
          </ErrorBoundary>
        </div>
      </div>
    </PageTransition>
  )
}
