import { useEffect, useState } from "react"
import { Outlet, NavLink, useNavigate, useLocation } from "react-router"
import TopNavBar from "./TopNavBar"
import CognitiveCoachDrawer from "./CognitiveCoachDrawer"
import { useStore } from "../../store/store"
import { icons } from "../ui/icons"

const NAV_ITEMS = [
  { to: "/", icon: icons.home, label: "Inicio", short: "Inicio", shortcut: "1", end: true },
  { to: "/paes", icon: icons.paes, label: "PAES", short: "PAES", shortcut: "2" },
  { to: "/gym", icon: icons.training, label: "Entrenamiento", short: "Entrenar" },
  { to: "/lab", icon: icons.analysis, label: "Análisis", short: "Análisis" },
  { to: "/settings", icon: icons.settings, label: "Ajustes", short: "Ajustes", shortcut: "4" },
  { to: "/admin", icon: icons.admin, label: "Admin", short: "Admin", shortcut: "5" },
]

export default function AppShell() {
  const navigate = useNavigate()
  const { toggleCoach, profile } = useStore()

  const location = useLocation()
  const [moreOpen, setMoreOpen] = useState(false)
  // Cierra el panel móvil "Otros" al cambiar de ruta.
  // Ajuste en tiempo de render, no setState en efecto, para mantener HMR estable.
  const pathname = location.pathname
  const [prevPath, setPrevPath] = useState(pathname)
  if (pathname !== prevPath) {
    setPrevPath(pathname)
    if (moreOpen) setMoreOpen(false)
  }

  const ADMIN_NAMES = ["drack", "drackv1", "hunther", "hunther4"]
  const isDrack = ADMIN_NAMES.includes(profile?.name?.trim().toLowerCase() || "")
  const _adminModules = import.meta.glob("../../pages/Admin.jsx")
  const hasAdmin = !!_adminModules["../../pages/Admin.jsx"]
  const navItems = isDrack && hasAdmin ? NAV_ITEMS : NAV_ITEMS.filter((item) => item.to !== "/admin")

  const homeItem = navItems[0]
  const paesItem = navItems[1]
  const otrosItems = navItems.slice(2, 4) // Gimnasio + Análisis
  const restItems = navItems.slice(4) // Ajustes (+ Admin)

  const primaryItems = [homeItem, paesItem]
  const isOtrosActive = otrosItems.some(
    (item) => item.to === pathname || (item.to !== "/" && pathname.startsWith(item.to))
  )

  // Atajos: teclas 1 a 6 y Ctrl+J para Coach
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.ctrlKey || e.metaKey) && (e.key === "j" || e.key === "J")) {
        e.preventDefault()
        toggleCoach()
        return
      }

      if (["INPUT", "TEXTAREA", "SELECT"].includes(e.target.tagName) || e.target.isContentEditable) {
        return
      }
      if (e.metaKey || e.ctrlKey || e.altKey) return

      // Atajo: usa navItems según si el perfil es admin
      const items = navItems
      // 3 = Otros (abre el panel con Gimnasio y Análisis)
      if (e.key === "3") {
        e.preventDefault()
        setMoreOpen((v) => !v)
        return
      }

      // El atajo 3 es Otros — ya se manejó arriba, no navegar directo
      const item = items.find((n) => n.shortcut === e.key && n.shortcut !== "3")
      if (item) {
        navigate(item.to)
      }
    }
    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [navigate, toggleCoach, isDrack])

  return (
    <div className="min-h-screen bg-[#101013] relative text-neutral-100">
      {/* Barra lateral — solo desktop */}
      <aside className="hidden lg:flex fixed left-0 top-0 h-full w-16 flex-col items-center py-4 gap-2 border-r border-white/[0.07] bg-[#17171b] z-40">
        <NavLink
          to="/"
          className="w-10 h-10 rounded-xl bg-[#525252] flex items-center justify-center text-white font-black text-lg mb-3"
          title="Peak — Inicio"
        >
          <span>P</span>
        </NavLink>

        <nav className="flex flex-col items-center gap-1.5 w-full px-2">
          {/* 1 y 2 */}
          {primaryItems.map((item) => {
            const Icon = item.icon
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `w-11 h-11 rounded-xl flex flex-col items-center justify-center relative transition-colors duration-200 group ${
                    isActive
                      ? "bg-[#2fc2c2]/15 text-[#2fc2c2]"
                      : "text-neutral-400 hover:bg-white/[0.06] hover:text-white"
                  }`
                }
                title={`${item.label} (Tecla ${item.shortcut})`}
                aria-label={item.label}
              >
                <Icon size={20} strokeWidth={1.5} />
                <span className="text-[9px] font-mono text-neutral-500 group-hover:text-neutral-400">
                  {item.shortcut}
                </span>
              </NavLink>
            )
          })}

          {/* 3 Otros + panel Gimnasio y Análisis */}
          <div className="w-full relative flex justify-center">
            <button
              type="button"
              onClick={() => setMoreOpen((v) => !v)}
              aria-expanded={moreOpen}
              aria-label="Otros"
              title="Otros (Tecla 3)"
              className={`w-11 h-11 rounded-xl flex flex-col items-center justify-center relative transition-colors duration-200 group ${
                isOtrosActive || moreOpen
                  ? "bg-[#2fc2c2]/15 text-[#2fc2c2]"
                  : "text-neutral-400 hover:bg-white/[0.06] hover:text-white"
              }`}
            >
              <icons.menu size={20} strokeWidth={1.5} />
              <span className="text-[9px] font-mono text-neutral-500 group-hover:text-neutral-400">3</span>
            </button>
            {moreOpen && (
              <div className="absolute left-full ml-2 top-0 z-50 w-48 border border-white/[0.08] bg-[#17171b] rounded-xl p-1.5 shadow-xl shadow-black/50">
                <div className="flex flex-col gap-1">
                  {otrosItems.map((item) => {
                    const Icon = item.icon
                    return (
                      <NavLink
                        key={item.to}
                        to={item.to}
                        end={item.end}
                        className={({ isActive }) =>
                          `flex items-center gap-3 rounded-xl px-3 py-2.5 transition-colors duration-200 ${
                            isActive ? "bg-[#2fc2c2]/15 text-[#2fc2c2]" : "text-neutral-300 hover:bg-white/[0.06]"
                          }`
                        }
                      >
                        <Icon size={20} strokeWidth={1.5} />
                        <span className="text-sm font-medium">{item.label}</span>
                      </NavLink>
                    )
                  })}
                </div>
              </div>
            )}
          </div>

          {/* Ajustes y Admin (fuera de Otros) */}
          {restItems.map((item) => {
            const Icon = item.icon
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `w-11 h-11 rounded-xl flex flex-col items-center justify-center relative transition-colors duration-200 group ${
                    isActive
                      ? "bg-[#2fc2c2]/15 text-[#2fc2c2]"
                      : "text-neutral-400 hover:bg-white/[0.06] hover:text-white"
                  }`
                }
                title={`${item.label} (Tecla ${item.shortcut})`}
                aria-label={item.label}
              >
                <Icon size={20} strokeWidth={1.5} />
                <span className="text-[9px] font-mono text-neutral-500 group-hover:text-neutral-400">
                  {item.shortcut}
                </span>
              </NavLink>
            )
          })}
        </nav>
      </aside>

      {/* Contenido principal */}
      <div className="lg:ml-16 flex flex-col min-h-screen">
        <TopNavBar />

        <main className="flex-1 w-full max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-5 lg:py-6 relative z-10 pb-28 lg:pb-10">
          <Outlet />
        </main>
      </div>

      {/* Navegación inferior — solo móvil */}
      <nav
        className="lg:hidden fixed bottom-0 left-0 right-0 z-50 border-t border-white/[0.08] bg-[#141416]/95 backdrop-blur-xl"
        style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
        aria-label="Navegación principal"
      >
        {/* Panel Otros (Gimnasio y Análisis + Ajustes + Coach) */}
        {moreOpen && (
          <div className="absolute bottom-full left-0 right-0 border-t border-white/[0.08] bg-[#141416]/98 px-4 py-3">
            <div className="flex flex-col gap-1">
              {[...otrosItems, ...restItems].map((item) => {
                const Icon = item.icon
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.end}
                    className={({ isActive }) =>
                      `flex items-center gap-3 rounded-xl px-3 py-3 min-h-[44px] transition-colors duration-200 ${
                        isActive ? "bg-[#2fc2c2]/15 text-[#2fc2c2]" : "text-neutral-300 active:bg-white/[0.06]"
                      }`
                    }
                  >
                    <Icon size={20} strokeWidth={1.5} />
                    <span className="text-sm font-medium">{item.label}</span>
                  </NavLink>
                )
              })}
              <button
                type="button"
                onClick={toggleCoach}
                className="flex items-center gap-3 rounded-xl px-3 py-3 min-h-[44px] text-left text-neutral-300 active:bg-white/[0.06] transition-colors"
              >
                <icons.coach size={20} strokeWidth={1.5} />
                <span className="text-sm font-medium">Coach</span>
              </button>
            </div>
          </div>
        )}
        <div className="flex items-stretch px-1">
          {primaryItems.map((item) => {
            const Icon = item.icon
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                aria-label={item.label}
                className={({ isActive }) =>
                  `flex flex-1 min-w-0 flex-col items-center justify-center gap-1 py-2 min-h-[56px] transition-colors duration-200 ${
                    isActive ? "text-[#2fc2c2]" : "text-neutral-500 active:text-neutral-300"
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    <Icon size={20} strokeWidth={isActive ? 2 : 1.5} />
                    <span className="text-[10px] leading-none truncate max-w-full px-1">
                      {item.short}
                    </span>
                  </>
                )}
              </NavLink>
            )
          })}
          <button
            type="button"
            onClick={() => setMoreOpen((v) => !v)}
            aria-expanded={moreOpen}
            aria-label="Otros"
            className={`flex flex-col items-center justify-center gap-1 py-2 min-h-[56px] flex-1 transition-colors ${
              isOtrosActive || moreOpen ? "text-[#2fc2c2]" : "text-neutral-500"
            }`}
          >
            <icons.menu size={20} strokeWidth={1.5} />
            <span className="text-[10px] leading-none">Otros</span>
          </button>
        </div>
      </nav>

      {/* Botón Coach — solo icono en celular para no tapar contenido */}
      <button
        type="button"
        onClick={toggleCoach}
        className="fixed bottom-20 right-4 lg:bottom-6 lg:right-6 z-40 flex items-center gap-2 p-3 lg:px-4 lg:py-2.5 rounded-2xl bg-[#1d1d20] border border-white/[0.12] text-neutral-200 hover:text-white hover:border-[#2fc2c2]/50 shadow-lg shadow-black/40 transition-colors duration-200 cursor-pointer"
        title="Abrir Coach (Ctrl + J)"
        aria-label="Abrir Coach"
      >
        <icons.coach size={20} strokeWidth={1.5} />
        <span className="hidden lg:inline text-xs font-semibold">Coach</span>
      </button>

      <CognitiveCoachDrawer />
    </div>
  )
}
