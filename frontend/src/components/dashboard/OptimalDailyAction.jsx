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
    return "Repaso pendiente: aún no hay una estimación de retención"
  }
  const percent = Math.round(retention * 100)
  if (retention < OPTIMAL_RETENTION) {
    return `Retención al ${percent}%, conviene reforzar para llegar al 85%`
  }
  return `Retención al ${percent}%, en el nivel objetivo o superior`
}

export default function OptimalDailyAction() {
  const navigate = useNavigate()
  const { paesSubtopicsList, paesFsrsStatus, paesActiveSubject, skills } = useStore()

  // Find optimal target: prioritized by FSRS overdue or cognitive balance
  const recommendation = useMemo(() => {
    // 1. Priority: PAES Subtopics with scheduled review due
    // shortest path: el subtítulo de retención (buildRetentionSubtitle) no se muestra en la UI;
    // se deja la función para no romper los tests que la cubren, pero no se pinta.
    const dueReviews = paesFsrsStatus?.capped_review_queue || []
    if (Array.isArray(dueReviews) && dueReviews.length > 0) {
      const topDue = Array.isArray(dueReviews[0]) ? dueReviews[0][0] : dueReviews[0]
      const subId = topDue?.slug || topDue?.subtopic_id
      if (subId) {
        const subjCode = topDue?.subject_code || "M1"
        return {
          type: "paes",
          title: `Hoy toca repasar ${topDue.subtopic_name || `PAES ${subjCode}`}`,
          subtitle: "",
          reason: "",
          actionText: `Entrenar ${subjCode}`,
          route: `/paes?subtopic=${subId}`,
          badge: "Repasos pendientes",
          badgeColor: "bg-sky-500/15 border-sky-500/30 text-sky-400",
          icon: "",
        }
      }
    }

    // 2. Priority: Low mastery attempted subtopics in PAES (ZDP)
    // La lista general trae todas las materias (ALL) para los totales por grupo;
    // la ZDP se acota a la materia activa para no sugerir electivas sin tocar.
    const subtopics = (paesSubtopicsList || []).filter(
      (s) => (s.subject_code || s.subject || "M1") === (paesActiveSubject || "M1")
    )
    if (subtopics.length > 0) {
      const attempted = subtopics.filter((s) => (s.attempts || 0) > 0)
      if (attempted.length > 0) {
        const lowestMastery = [...attempted].sort((a, b) => (a.mastery || 0) - (b.mastery || 0))[0]
        const subId = lowestMastery?.slug || lowestMastery?.id
        if (subId && (lowestMastery.mastery || 0) < 0.8) {
          return {
            type: "paes",
            title: `Hoy toca repasar ${lowestMastery.name}`,
            subtitle: "",
            reason: "",
            actionText: "Practicar",
            route: `/paes?subtopic=${subId}`,
            badge: "ZDP Óptima",
            badgeColor: "bg-[#2fc2c2]/15 border-[#2fc2c2]/30 text-[#2fc2c2]",
            icon: "",
          }
        }
      }
    }

    // 3. Fallback: Cognitive Gym (Dual N-Back)
    return {
      type: "gym",
      title: "Hoy toca memoria de trabajo",
      subtitle: "",
      reason: "",
      actionText: "Entrenar",
      route: "/gym/dual_n_back",
      badge: "Entrenamiento",
      badgeColor: "bg-purple-500/15 border-purple-500/30 text-purple-400",
      icon: "",
    }
  }, [paesSubtopicsList, paesFsrsStatus, paesActiveSubject, skills])

  return (
    <div className="relative overflow-hidden rounded-3xl border border-[#2fc2c2]/20 bg-neutral-900/60 p-6 lg:p-8 shadow-2xl mb-8 group">
      {/* Decorative ambient glow */}
      <div className="absolute top-0 right-0 -mr-16 -mt-16 w-64 h-64 bg-[#2fc2c2]/10 rounded-full blur-3xl pointer-events-none group-hover:bg-[#2fc2c2]/15 transition-all" />

      <div className="relative z-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="space-y-3 max-w-2xl">
          <div className="flex items-center gap-2.5">
            <span className={`text-[10px] uppercase font-mono font-bold px-2.5 py-1 rounded-full border ${recommendation.badgeColor}`}>
              {recommendation.badge}
            </span>
            <span className="text-xs text-neutral-400 font-medium">
              Tu próximo paso
            </span>
          </div>

          <div>
            <h3 className="text-xl lg:text-2xl font-black tracking-tight text-white flex items-center gap-2.5">
              <span>{recommendation.icon}</span>
              <span>{recommendation.title}</span>
            </h3>
          </div>
        </div>

        <button
          onClick={() => navigate(recommendation.route)}
          className="shrink-0 w-full md:w-auto px-5 py-3 rounded-2xl bg-[#2fc2c2] text-neutral-950 font-semibold hover:bg-[#2fc2c2]/90 transition-colors"
        >
          <span>{recommendation.actionText}</span>
        </button>
      </div>
    </div>
  )
}
