import React from "react"

export function FsrsStatusWidget({ fsrsStatus, onReviewDueClick, onReviewSubtopic }) {
  if (!fsrsStatus) return null

  const dueCount = fsrsStatus.due_for_review_count || 0
  const queue = Array.isArray(fsrsStatus.capped_review_queue) ? fsrsStatus.capped_review_queue : []
  const cappedCount = queue.length

  return (
    <div className="bg-neutral-900/60 border border-white/[0.08] rounded-2xl p-5 backdrop-blur-xl mb-6 shadow-xl">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-bold uppercase tracking-wider text-[#2fc2c2] bg-[#2fc2c2]/10 px-2.5 py-1 rounded-full border border-[#2fc2c2]/20">
              Repasos
            </span>
            <span className="text-xs text-neutral-400">
              Máximo {fsrsStatus.review_capping_limit || 5} repaso(s) al día
            </span>
          </div>
          <h3 className="text-lg font-bold text-white">
            Tu memoria y tus repasos {fsrsStatus.subject_code ? `(${fsrsStatus.subject_code})` : ""}
          </h3>
        </div>

        <div className="flex items-center gap-3">
          <div className="bg-neutral-800/80 border border-white/[0.06] px-4 py-2 rounded-xl text-center">
            <div className="text-2xl font-black text-amber-400">{dueCount}</div>
            <div className="text-[11px] font-medium text-neutral-400">Por repasar</div>
          </div>
          <div className="bg-neutral-800/80 border border-white/[0.06] px-4 py-2 rounded-xl text-center">
            <div className="text-2xl font-black text-[#2fc2c2]">{cappedCount}</div>
            <div className="text-[11px] font-medium text-neutral-400">Objetivo de hoy</div>
          </div>
        </div>
      </div>

      {cappedCount > 0 && (
        <div className="mt-4 pt-4 border-t border-white/[0.06] space-y-3">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <span className="text-xs text-neutral-300 font-medium">
              Subtemas para reforzar hoy:
            </span>
            {onReviewDueClick && (
              <button
                onClick={onReviewDueClick}
                className="btn btn-secondary px-3.5 py-1.5 text-xs"
              >
                 Repasar ahora ({cappedCount})
              </button>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            {queue.map((item, idx) => (
              <div
                key={item.subtopic_id || idx}
                className="p-3 rounded-xl bg-neutral-800/60 border border-white/[0.06] hover:border-white/[0.12] flex items-center justify-between gap-3 text-xs transition-all"
              >
                <div className="min-w-0">
                  <div className="font-bold text-white truncate">{item.subtopic_name}</div>
                  <div className="text-[10px] text-neutral-400 font-mono flex items-center gap-2 mt-0.5">
                    <span className="text-[#2fc2c2]">
                      Retención: {Math.round((item.projected_retention || item.projected_r || 0.8) * 100)}%
                    </span>
                    <span>•</span>
                    <span>Nivel: {item.leitner_box || 1}</span>
                  </div>
                </div>
                {onReviewSubtopic && item.slug && (
                  <button
                    onClick={() => onReviewSubtopic(item.slug)}
                    className="shrink-0 px-2.5 py-1 bg-white/[0.08] hover:bg-white text-white hover:text-neutral-950 font-bold text-[11px] rounded-lg transition-all cursor-pointer"
                  >
                    Repasar 
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
