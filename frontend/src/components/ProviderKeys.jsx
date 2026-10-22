import { useEffect, useState } from "react"
import { api } from "../api/client"
import { useToast } from "./ui/Toast"

const PROVIDERS = [
  { id: "groq", label: "Groq", icon: "⚡" },
  { id: "openrouter", label: "OpenRouter", icon: "🌐" },
  { id: "generalcompute", label: "General Compute", icon: "⚙" },
]

export default function ProviderKeys() {
  const toast = useToast()
  const [status, setStatus] = useState({})
  const [values, setValues] = useState({})
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(null)

  const loadStatus = async () => {
    try {
      const data = await api.models.getKeys()
      setStatus(data)
    } catch (e) {
      console.warn("[ProviderKeys] getKeys error:", e.message)
    }
  }

  useEffect(() => {
    loadStatus()
  }, [])

  const handleSave = async (provider) => {
    const key = (values[provider] || "").trim()
    if (!key) return
    setSaving(provider)
    setErrors((prev) => ({ ...prev, [provider]: null }))
    try {
      const res = await api.models.setKey(provider, key)
      setStatus((prev) => ({
        ...prev,
        [provider]: { configured: res.configured, masked: res.masked },
      }))
      setValues((prev) => ({ ...prev, [provider]: "" }))
      toast?.success("API key guardada correctamente")
    } catch (e) {
      setErrors((prev) => ({ ...prev, [provider]: e.message }))
    } finally {
      setSaving(null)
    }
  }

  const handleClear = async (provider) => {
    setSaving(provider)
    setErrors((prev) => ({ ...prev, [provider]: null }))
    try {
      const res = await api.models.setKey(provider, "")
      setStatus((prev) => ({
        ...prev,
        [provider]: { configured: res.configured, masked: res.masked },
      }))
      setValues((prev) => ({ ...prev, [provider]: "" }))
      toast?.success("API key eliminada")
    } catch (e) {
      setErrors((prev) => ({ ...prev, [provider]: e.message }))
    } finally {
      setSaving(null)
    }
  }

  return (
    <div className="space-y-3" data-testid="provider-keys">
      {PROVIDERS.map((p) => {
        const info = status[p.id] || { configured: false, masked: null }
        return (
          <div
            key={p.id}
            className="bg-white/[0.02] border border-white/[0.06] rounded-xl p-3 space-y-2"
            data-testid={`provider-key-${p.id}`}
          >
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2 min-w-0">
                <span className="text-sm">{p.icon}</span>
                <p className="text-xs font-semibold text-white truncate">{p.label}</p>
                {info.configured ? (
                  <span className="text-[9px] font-bold uppercase tracking-wider text-green-400/80 border border-green-500/20 bg-green-500/10 px-1.5 py-0.5 rounded-full">
                    {info.masked}
                  </span>
                ) : (
                  <span className="text-[9px] font-bold uppercase tracking-wider text-neutral-500 border border-white/[0.06] bg-white/[0.03] px-1.5 py-0.5 rounded-full">
                    sin key
                  </span>
                )}
              </div>
            </div>

            <div className="flex items-center gap-2">
              <input
                type="password"
                autoComplete="off"
                spellCheck={false}
                placeholder={info.configured ? "•••••••• (reemplazar)" : "Pegar API key"}
                aria-label={`API key de ${p.label}`}
                value={values[p.id] || ""}
                onChange={(e) =>
                  setValues((prev) => ({ ...prev, [p.id]: e.target.value }))
                }
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleSave(p.id)
                }}
                className="flex-1 min-w-0 bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-1.5 text-xs text-white placeholder-neutral-600 focus:outline-none focus:border-cyan-500/40"
              />
              <button
                onClick={() => handleSave(p.id)}
                disabled={saving === p.id || !(values[p.id] || "").trim()}
                className="px-3 py-1.5 rounded-lg text-[10px] font-bold uppercase tracking-wider text-cyan-400 bg-cyan-500/10 border border-cyan-500/20 hover:bg-cyan-500/20 transition-all duration-200 disabled:opacity-40"
              >
                {saving === p.id ? "..." : "Guardar"}
              </button>
              <button
                onClick={() => handleClear(p.id)}
                disabled={saving === p.id || !info.configured}
                className="px-3 py-1.5 rounded-lg text-[10px] font-bold uppercase tracking-wider text-red-400 bg-red-500/10 border border-red-500/20 hover:bg-red-500/20 transition-all duration-200 disabled:opacity-40"
              >
                Limpiar
              </button>
            </div>

            {errors[p.id] && (
              <p role="alert" className="text-[11px] text-red-400">
                {errors[p.id]}
              </p>
            )}
          </div>
        )
      })}
    </div>
  )
}
