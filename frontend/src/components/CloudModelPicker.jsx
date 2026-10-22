import { useCallback, useEffect, useState } from "react"
import { api } from "../api/client"
import { useStore } from "../store/store"
import { useToast } from "./ui/Toast"

const CLOUD_PROVIDERS = [
  { id: "groq", label: "Groq", icon: "⚡" },
  { id: "openrouter", label: "OpenRouter", icon: "🌐" },
  { id: "generalcompute", label: "General Compute", icon: "⚙" },
]

export default function CloudModelPicker() {
  const { selectedModel, selectModel, selectModelAuto, fetchAiStatus } = useStore()
  const toast = useToast()
  const [provider, setProvider] = useState("groq")
  const [models, setModels] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [selected, setSelected] = useState("auto")
  const [saving, setSaving] = useState(false)

  const fetchModels = useCallback(async (p) => {
    setLoading(true)
    setError(null)
    setModels([])
    try {
      const data = await api.models.getAvailableForKey(p)
      setModels(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchModels(provider)
  }, [provider, fetchModels])

  const handleProviderChange = (p) => {
    setProvider(p)
    setSelected("auto")
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      if (selected === "auto") {
        await selectModelAuto()
        toast?.success("Selección automática activada")
      } else {
        const model = models.find((m) => m.model_id === selected)
        if (!model) return
        const name = model.name || model.model_id
        await selectModel(name, provider, model.model_id)
        toast?.success(`Modelo cambiado a ${name}`)
      }
      fetchAiStatus?.()
    } catch (e) {
      toast?.error?.(e.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-3" data-testid="cloud-model-picker">
      {/* Provider tabs */}
      <div className="flex bg-white/[0.03] rounded-xl p-1 border border-white/[0.06]">
        {CLOUD_PROVIDERS.map((p) => (
          <button
            key={p.id}
            onClick={() => handleProviderChange(p.id)}
            className={`flex-1 px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider rounded-lg transition-all duration-200 ${
              provider === p.id
                ? "bg-cyan-500/15 text-cyan-400 border border-cyan-500/20"
                : "text-neutral-600 hover:text-neutral-400 border border-transparent"
            }`}
          >
            {p.icon} {p.label}
          </button>
        ))}
      </div>

      {/* Live model list for the stored key */}
      <div className="max-h-64 overflow-y-auto space-y-1.5 pr-1">
        {loading && (
          <p className="text-xs text-neutral-500 py-3 text-center" data-testid="picker-loading">
            Cargando modelos disponibles…
          </p>
        )}

        {!loading && error && (
          <p role="alert" className="text-xs text-red-400 py-3 text-center" data-testid="picker-error">
            {error}
          </p>
        )}

        {!loading && !error && models.length === 0 && (
          <p className="text-xs text-neutral-600 py-3 text-center">
            Sin modelos disponibles para esta key.
          </p>
        )}

        {!loading && !error && models.length > 0 && (
          <label
            className={`flex items-center gap-3 p-2.5 rounded-xl border cursor-pointer transition-all duration-200 ${
              selected === "auto"
                ? "border-green-500/40 bg-green-500/10"
                : "border-white/[0.06] bg-white/[0.02] hover:bg-white/[0.04]"
            }`}
            onClick={() => setSelected("auto")}
          >
            <div
              className={`w-4 h-4 rounded-full border-2 flex items-center justify-center shrink-0 ${
                selected === "auto" ? "border-green-400" : "border-neutral-600"
              }`}
            >
              {selected === "auto" && <div className="w-2 h-2 rounded-full bg-green-400" />}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold text-white">Recomendada (automática)</p>
              <p className="text-[10px] text-neutral-600 mt-0.5">
                El router elige el mejor modelo para cada tarea
              </p>
            </div>
          </label>
        )}

        {!loading &&
          !error &&
          models.map((m) => (
            <label
              key={m.model_id}
              data-testid={`picker-model-${m.model_id}`}
              className={`flex items-center gap-3 p-2.5 rounded-xl border cursor-pointer transition-all duration-200 ${
                selected === m.model_id
                  ? "border-cyan-500/40 bg-cyan-500/10"
                  : "border-white/[0.06] bg-white/[0.02] hover:bg-white/[0.04]"
              }`}
              onClick={() => setSelected(m.model_id)}
            >
              <div
                className={`w-4 h-4 rounded-full border-2 flex items-center justify-center shrink-0 ${
                  selected === m.model_id ? "border-cyan-400" : "border-neutral-600"
                }`}
              >
                {selected === m.model_id && <div className="w-2 h-2 rounded-full bg-cyan-400" />}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-semibold text-white truncate">{m.name || m.model_id}</p>
                <p className="text-[10px] text-neutral-600 mt-0.5 truncate">{m.model_id}</p>
              </div>
            </label>
          ))}
      </div>

      <div className="flex justify-end pt-1">
        <button
          onClick={handleSave}
          disabled={saving || (selected !== "auto" && !models.some((m) => m.model_id === selected))}
          className="btn btn-primary text-xs"
        >
          {saving ? "Guardando..." : "Guardar selección"}
        </button>
      </div>

      {/* Selección actual (solo lectura, informativa) */}
      {selectedModel && !selectedModel.auto && (
        <p className="text-[10px] text-neutral-600 text-right">
          Actual: {selectedModel.model_name} · {selectedModel.provider}
        </p>
      )}
    </div>
  )
}
