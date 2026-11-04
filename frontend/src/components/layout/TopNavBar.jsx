import { useLocation } from "react-router"
import { useStore } from "../../store/store"
import { icons, SUBJECT_ICONS } from "../ui/icons"

const ROUTE_NAMES = {
  "/": { title: "Inicio" },
  "/gym": { title: "Entrenamiento" },
  "/paes": { title: "PAES" },
  "/lab": { title: "Análisis" },
  "/settings": { title: "Ajustes" },
  "/admin": { title: "Admin" },
}

export default function TopNavBar() {
  const location = useLocation()
  const { profile, summary, paesActiveSubject } = useStore()

  const basePath = Object.keys(ROUTE_NAMES).find(
    (p) => p === location.pathname || (p !== "/" && location.pathname.startsWith(p))
  ) || "/"

  const routeMeta = ROUTE_NAMES[basePath] || ROUTE_NAMES["/"]
  const streak = summary?.streak_days ?? profile?.streak ?? 0
  const isPaesRoute = basePath === "/paes"
  const activeSubject = paesActiveSubject || "M1"
  const SubjectIcon = SUBJECT_ICONS[activeSubject] || SUBJECT_ICONS.M1
  const StreakIcon = icons.streak

  return (
    <header className="sticky top-0 z-30 w-full border-b border-white/[0.07] bg-[#101013]/90 backdrop-blur-lg">
      <div className="w-full max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between gap-3">
        <div className="min-w-0">
          <h1 className="text-sm font-semibold tracking-tight text-white truncate">
            {routeMeta.title}
          </h1>
        </div>

        <div className="flex items-center gap-2">
          {streak > 0 && (
            <div
              className="flex items-center gap-1.5 px-2.5 h-9 rounded-lg bg-white/[0.04] border border-white/[0.08] text-neutral-300 text-xs font-medium"
              title={`${streak} días consecutivos`}
            >
              <StreakIcon size={15} strokeWidth={1.5} className="text-amber-400" />
              <span className="font-mono font-semibold text-neutral-200">{streak}</span>
              <span className="hidden sm:inline text-neutral-400">días</span>
            </div>
          )}

          {isPaesRoute && (
            <div
              className="flex items-center gap-1.5 px-2.5 h-9 rounded-lg bg-white/[0.04] border border-white/[0.08] text-neutral-300 text-xs font-medium"
              title={`Escala DEMRE 100–1000 · ${activeSubject}`}
            >
              <SubjectIcon size={15} strokeWidth={1.5} className="text-[#2fc2c2]" />
              <span className="font-mono font-semibold">{activeSubject}</span>
            </div>
          )}

          <div
            className="flex items-center gap-2 pl-2 border-l border-white/[0.08]"
            title={profile?.name || "Perfil"}
          >
            <div className="w-9 h-9 rounded-lg bg-[#525252] flex items-center justify-center text-white font-bold text-xs">
              {profile?.name ? profile.name.slice(0, 2).toUpperCase() : "PK"}
            </div>
            {profile?.name && (
              <span className="hidden lg:block text-xs font-medium text-neutral-300 max-w-[110px] truncate">
                {profile.name}
              </span>
            )}
          </div>
        </div>
      </div>
    </header>
  )
}
