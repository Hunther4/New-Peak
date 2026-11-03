import { useEffect, useState, useCallback } from "react"
import { api } from "../api/client"

const REFRESH_INTERVAL_MS = 10_000

function formatMinutesAgo(minutes) {
  if (minutes === 0) return "ahora mismo"
  if (minutes === 1) return "hace 1 minuto"
  if (minutes < 60) return `hace ${minutes} min`
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return m > 0 ? `hace ${h}h ${m}min` : `hace ${h}h`
}

function ScoreBadge({ min, max }) {
  if (min == null) return <span className="text-neutral-500 text-xs">sin estimación</span>
  return (
    <span className="text-emerald-400 font-mono text-sm font-semibold">
      {min}–{max} pts
    </span>
  )
}

function SessionRow({ sess, index }) {
  const pctColor =
    sess.pct >= 70
      ? "text-emerald-400"
      : sess.pct >= 50
      ? "text-yellow-400"
      : "text-red-400"

  return (
    <tr className="border-t border-white/[0.04]">
      <td className="py-1.5 pr-3 text-neutral-400 text-xs">#{index + 1}</td>
      <td className="py-1.5 pr-3 text-xs text-neutral-300">
        {sess.items} preguntas
      </td>
      <td className={`py-1.5 pr-3 text-xs font-mono ${pctColor}`}>
        {sess.correct}/{sess.items} ({sess.pct}%)
      </td>
      <td className="py-1.5 text-xs">
        <ScoreBadge min={sess.score_min} max={sess.score_max} />
      </td>
    </tr>
  )
}

function SubjectCard({ subject }) {
  return (
    <div className="bg-neutral-900/60 rounded-xl border border-white/[0.06] p-4">
      <div className="flex items-center justify-between mb-3">
        <div>
          <span className="text-emerald-400 font-bold text-sm">{subject.code}</span>
          <span className="text-neutral-400 text-xs ml-2">{subject.name}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-neutral-500 text-xs">{subject.session_count} ensayo{subject.session_count !== 1 ? "s" : ""}</span>
          <ScoreBadge min={subject.best_score_min} max={subject.best_score_max} />
        </div>
      </div>
      {subject.sessions.length > 0 && (
        <table className="w-full">
          <tbody>
            {subject.sessions.map((sess, i) => (
              <SessionRow key={i} sess={sess} index={i} />
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

function UserCard({ user }) {
  const isOnline = user.is_online
  const hasActivity = user.subjects.length > 0

  return (
    <div
      className={`rounded-2xl border p-5 transition-all ${
        isOnline
          ? "border-emerald-500/30 bg-emerald-950/20 shadow-lg shadow-emerald-900/10"
          : "border-white/[0.06] bg-neutral-900/40"
      }`}
    >
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <div
          className={`w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold shrink-0 ${
            isOnline
              ? "bg-emerald-500/20 text-emerald-400 ring-2 ring-emerald-500/40"
              : "bg-neutral-800 text-neutral-400"
          }`}
        >
          {(user.name || user.email)[0].toUpperCase()}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-bold text-neutral-100 truncate">{user.name || user.email}</p>
          <p className="text-xs text-neutral-500">
            {user.name ? `${user.email} · ` : ""}{formatMinutesAgo(user.last_seen_minutes_ago)}
          </p>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          <span
            className={`w-2 h-2 rounded-full ${
              isOnline ? "bg-emerald-400 animate-pulse" : "bg-neutral-600"
            }`}
          />
          <span
            className={`text-xs font-medium ${
              isOnline ? "text-emerald-400" : "text-neutral-500"
            }`}
          >
            {isOnline ? "En línea" : "Offline"}
          </span>
        </div>
      </div>

      {/* Activity */}
      {hasActivity ? (
        <div className="space-y-3">
          {user.subjects.map((subject) => (
            <SubjectCard key={subject.code} subject={subject} />
          ))}
        </div>
      ) : (
        <p className="text-neutral-600 text-sm text-center py-3">
          Sin ensayos completados aún
        </p>
      )}
    </div>
  )
}

export default function Admin() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [lastRefresh, setLastRefresh] = useState(null)
  const [loading, setLoading] = useState(true)

  const fetchData = useCallback(async () => {
    try {
      const result = await api.request("/admin/live-monitor")
      setData(result)
      setError(null)
      setLastRefresh(new Date())
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, REFRESH_INTERVAL_MS)
    return () => clearInterval(interval)
  }, [fetchData])

  return (
    <div className="min-h-screen bg-neutral-950 p-4 lg:p-8">
      <div className="max-w-3xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-1">
            <span className="text-2xl">🗼</span>
            <h1 className="text-2xl font-bold text-neutral-100">Torre de Control</h1>
          </div>
          <p className="text-neutral-500 text-sm">
            Familiares y amigos conectados a New Peak
          </p>
          {lastRefresh && (
            <p className="text-neutral-700 text-xs mt-1">
              Actualizado {lastRefresh.toLocaleTimeString("es-CL")} · refresca cada 10s
            </p>
          )}
        </div>

        {/* Loading */}
        {loading && (
          <div className="flex items-center justify-center py-20">
            <div className="w-6 h-6 border-2 border-neutral-700 border-t-emerald-500 rounded-full animate-spin" />
          </div>
        )}

        {/* Error */}
        {error && !loading && (
          <div className="bg-red-950/40 border border-red-500/20 rounded-xl p-5 text-red-400 text-sm space-y-3">
            <div className="flex items-center justify-between">
              <span className="font-semibold">Error al cargar: {error}</span>
              <button
                onClick={fetchData}
                className="px-3 py-1.5 text-xs bg-red-500/20 hover:bg-red-500/30 text-red-200 rounded-lg transition"
              >
                Reintentar
              </button>
            </div>
            <div className="pt-2 border-t border-red-500/10 flex items-center justify-between text-xs text-neutral-400">
              <span>¿Eres el administrador? Identifícate para desbloquear la consola:</span>
              <button
                onClick={() => {
                  localStorage.setItem("peak_user_name", "Drack")
                  fetchData()
                }}
                className="px-3 py-1.5 bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 font-medium rounded-lg transition"
              >
                Acceder como Drack 🗼
              </button>
            </div>
          </div>
        )}

        {/* Data */}
        {data && !loading && (
          <>
            {/* Online counter */}
            <div className="flex items-center gap-4 mb-6">
              <div
                className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium border ${
                  data.online_count > 0
                    ? "bg-emerald-950/40 border-emerald-500/30 text-emerald-400"
                    : "bg-neutral-900 border-white/[0.06] text-neutral-500"
                }`}
              >
                <span
                  className={`w-2 h-2 rounded-full ${
                    data.online_count > 0 ? "bg-emerald-400 animate-pulse" : "bg-neutral-600"
                  }`}
                />
                {data.online_count > 0
                  ? `${data.online_count} conectado${data.online_count !== 1 ? "s" : ""} ahora`
                  : "Nadie conectado ahora"}
              </div>
              <span className="text-neutral-600 text-xs">
                {data.users.length} usuario{data.users.length !== 1 ? "s" : ""} con actividad reciente
              </span>
            </div>

            {/* User list */}
            {data.users.length === 0 ? (
              <div className="text-center py-16">
                <p className="text-neutral-600 text-lg mb-2">Nadie conectado aún</p>
                <p className="text-neutral-700 text-sm">
                  Comparte el enlace por WhatsApp para que se unan 🎉
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {data.users.map((user) => (
                  <UserCard key={user.user_id} user={user} />
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
