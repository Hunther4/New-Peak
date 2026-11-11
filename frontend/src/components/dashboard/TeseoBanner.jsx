import { useState } from "react"
import { icons } from "../ui/icons"

const DISMISSED_KEY = "peak_teseo_dismissed"

export default function TeseoBanner() {
  const [expandido, setExpandido] = useState(false)
  const [cerrado, setCerrado] = useState(() => {
    try {
      return localStorage.getItem(DISMISSED_KEY) === "true"
    } catch {
      return false
    }
  })

  if (cerrado) return null

  const handleCerrar = (e) => {
    e.stopPropagation()
    setCerrado(true)
    try {
      localStorage.setItem(DISMISSED_KEY, "true")
    } catch {}
  }

  // Arranca plegado: solo se ve el título y el usuario decide si lo abre.
  return (
    <section className="mb-6">
      <div className="rounded-2xl bg-white/[0.02] border border-white/[0.06] relative">
        <button
          type="button"
          onClick={() => setExpandido(!expandido)}
          className="w-full px-4 py-3 text-left flex items-center gap-3 cursor-pointer"
          aria-expanded={expandido}
        >
          <icons.paes size={16} strokeWidth={1.6} className="text-amber-200/70 shrink-0" />
          <h4 className="flex-1 text-xs font-medium text-amber-200">
            El Barco de Teseo
          </h4>
          <span className="text-xs text-neutral-400 font-medium" style={{ marginRight: 44 }}>
            {expandido ? "Ocultar" : "Leer"}
          </span>
        </button>

        {expandido && (
          <div className="px-4 pb-4 -mt-1">
            <p className="text-sm text-neutral-300 leading-relaxed">
              “Es gracioso como quizá el 80-90% de nosotros creemos que unas simples pruebas definirán nuestro futuro. Esto me hace pensar en el dilema del barco de Teseo: ¿qué somos nosotros si no un cuerpo que se renueva a sí mismo continuamente, qué somos nosotros sin esta prueba? Al final la respuesta es simple y tonta incluso: somos nosotros y lo que decidamos hacer. Ánimo en lo que hagas, ahora y en el futuro.”
            </p>
          </div>
        )}

        <button
          type="button"
          onClick={handleCerrar}
          aria-label="Cerrar reflexión"
          className="absolute top-1 right-2 w-8 h-8 flex items-center justify-center rounded-full text-neutral-500 hover:text-neutral-200 hover:bg-white/[0.08] transition-colors cursor-pointer"
        >
          <icons.close size={14} strokeWidth={1.8} />
        </button>
      </div>
    </section>
  )
}
