import { useMemo } from "react"
import { useNavigate } from "react-router"
import { useStore } from "../../store/store"

// Optimal retention target used by the FSRS review queue.
const OPTIMAL_RETENTION = 0.85

/**
 * Builds the retention claim from the item's own measured retention.
 * The claim is never made when the item carries no retention value.
 */
function buildRetentionSubtitle(item) {
  const raw = item?.projected_retention ?? item?.projected_r
  const retention = typeof raw === "number" ? raw : Number(raw)
  if (raw === null || raw === undefined || !Number.isFinite(retention)) {
    return "FSRS review pending — no retention estimate available"
  }
  const percent = Math.round(retention * 100)
  if (retention < OPTIMAL_RETENTION) {
    return `FSRS retention at ${percent}% — needs reinforcement to reach the 85% target`
  }
  return `FSRS retention at ${percent}% — at or above the 85% target`
}

export default function OptimalDailyAction() {
  const navigate = useNavigate()
  const { paesSubtopicsList, paesFsrsStatus, skills } = useStore()

  // Find optimal target: prioritized by FSRS overdue or cognitive balance
  const recommendation = useMemo(() => {
    // 1. Priority: PAES Subtopics with scheduled review due
    const dueReviews = paesFsrsStatus?.capped_review_queue || []
    if (Array.isArray(dueReviews) && dueReviews.length > 0) {
      const topDue = Array.isArray(dueReviews[0]) ? dueReviews[0][0] : dueReviews[0]
      const subId = topDue?.slug || topDue?.subtopic_id
      if (subId) {
        const subjCode = topDue?.subject_code || "M1"
        return {
          type: "paes",
          title: `Repaso Curricular: ${topDue.subtopic_name || `PAES ${subjCode}`}`,
          subtitle: buildRetentionSubtitle(topDue),
          reason: "Tu memoria a largo plazo requiere afianzar este subtema antes de avanzar a prerrequisitos superiores.",
          actionText: `Entrenar Subtema en PAES ${subjCode}`,
          route: `/paes?subtopic=${subId}`,
          badge: "FSRS v4.5 Pendiente",
          badgeColor: "bg-sky-500/15 border-sky-500/30 text-sky-400",
          icon: subjCode === "M1" || subjCode === "M2" ? "📐" : subjCode === "CIENCIAS" ? "🧪" : "📖",
        }
      }
    }

    // 2. Priority: Low mastery attempted subtopics in PAES (ZDP)
    const subtopics = paesSubtopicsList || []
    if (subtopics.length > 0) {
      const attempted = subtopics.filter((s) => (s.attempts || 0) > 0)
      if (attempted.length > 0) {
        const lowestMastery = [...attempted].sort((a, b) => (a.mastery || 0) - (b.mastery || 0))[0]
        const subId = lowestMastery?.slug || lowestMastery?.id
        if (subId && (lowestMastery.mastery || 0) < 0.8) {
          return {
            type: "paes",
            title: `Fortalecer: ${lowestMastery.name}`,
            subtitle: `Nivel de maestría actual: ${Math.round((lowestMastery.mastery || 0) * 100)}%`,
            reason: "Identificado en tu Zona de Desarrollo Próximo (ZDP). Resolver 5 ítems aquí elevará tu puntaje estimado.",
            actionText: "Practicar con Tutor Socrático",
            route: `/paes?subtopic=${subId}`,
            badge: "ZDP Óptima",
            badgeColor: "bg-emerald-500/15 border-emerald-500/30 text-emerald-400",
            icon: "🧠",
          }
        }
      }
    }

    // 3. Fallback: Cognitive Gym (Dual N-Back)
    return {
      type: "gym",
      title: "Estimulación Cognitiva: Dual N-Back",
      subtitle: "Ampliación de memoria de trabajo",
      reason: "La práctica deliberada de memoria operativa potencia la velocidad de procesamiento matemático en la PAES.",
      actionText: "Iniciar Desafío Dual N-Back",
      route: "/gym/dual_n_back",
      badge: "Gimnasio Psicométrico",
      badgeColor: "bg-purple-500/15 border-purple-500/30 text-purple-400",
      icon: "⚡",
    }
  }, [paesSubtopicsList, paesFsrsStatus, skills])

  return (
    <div className="relative overflow-hidden rounded-3xl border border-emerald-500/20 bg-gradient-to-br from-emerald-950/40 via-neutral-900/60 to-neutral-950 p-6 lg:p-8 shadow-2xl mb-8 backdrop-blur-xl group">
      {/* Decorative ambient glow */}
      <div className="absolute top-0 right-0 -mr-16 -mt-16 w-64 h-64 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none group-hover:bg-emerald-500/15 transition-all" />

      <div className="relative z-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="space-y-3 max-w-2xl">
          <div className="flex items-center gap-2.5">
            <span className={`text-[10px] uppercase font-mono font-bold px-2.5 py-1 rounded-full border ${recommendation.badgeColor}`}>
              {recommendation.badge}
            </span>
            <span className="text-xs text-neutral-400 font-medium">
              Recomendación de Práctica Deliberada
            </span>
          </div>

          <div>
            <h3 className="text-xl lg:text-2xl font-black tracking-tight text-white flex items-center gap-2.5">
              <span>{recommendation.icon}</span>
              <span>{recommendation.title}</span>
            </h3>
            <p className="text-sm font-medium text-emerald-300/80 mt-1" data-testid="optimal-daily-action-subtitle">
              {recommendation.subtitle}
            </p>
          </div>

          <p className="text-xs text-neutral-400 leading-relaxed">
            {recommendation.reason}
          </p>
        </div>

        <button
          onClick={() => navigate(recommendation.route)}
          className="shrink-0 w-full md:w-auto px-6 py-3.5 rounded-2xl bg-gradient-to-r from-emerald-500 to-green-400 text-black font-extrabold text-sm tracking-wide shadow-xl shadow-emerald-500/25 hover:shadow-emerald-500/40 hover:scale-[1.02] active:scale-[0.98] transition-all flex items-center justify-center gap-2 cursor-pointer"
        >
          <span>{recommendation.actionText}</span>
          <span className="text-base">➔</span>
        </button>
      </div>
    </div>
  )
}
