import React, { useState, useEffect, useRef, useMemo } from "react"
import { useLocation } from "react-router"
import { useStore } from "../../store/store"
import { MathRenderer } from "../paes/MathRenderer"

export default function CognitiveCoachDrawer() {
  const location = useLocation()
  const [inputText, setInputText] = useState("")
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  const {
    isCoachOpen,
    closeCoach,
    clearCoachMessages,
    coachMessages,
    coachLoading,
    coachError,
    sendCoachMessage,
    paesActiveQuestion,
    paesActiveSubject,
    paesSubtopic,
    gameSession,
    mathSession,
    iqSession,
  } = useStore()

  // Auto-scroll on new messages
  useEffect(() => {
    if (isCoachOpen && typeof messagesEndRef.current?.scrollIntoView === "function") {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" })
    }
  }, [coachMessages, coachLoading, isCoachOpen])

  // Focus input on open & handle Escape key
  useEffect(() => {
    if (isCoachOpen) {
      setTimeout(() => inputRef.current?.focus(), 150)
      const handleKeyDown = (e) => {
        if (e.key === "Escape") {
          closeCoach()
        }
      }
      window.addEventListener("keydown", handleKeyDown)
      return () => window.removeEventListener("keydown", handleKeyDown)
    }
  }, [isCoachOpen, closeCoach])

  // Determine current contextual chip
  const contextMeta = useMemo(() => {
    const path = location.pathname || ""
    if (paesActiveQuestion || path.includes("/paes")) {
      const sub = paesActiveSubject || paesActiveQuestion?.subject || "M1"
      const topic = paesActiveQuestion?.subtopic || paesSubtopic?.name || "Ejercitación"
      return {
        icon: "📐",
        label: `PAES ${sub} · ${topic}`,
        category: "paes",
      }
    }
    if (path.includes("/gym")) {
      let gameName = "Entrenamiento Cognitivo"
      if (gameSession) gameName = `Dual N-Back (N=${gameSession.current_n || 2})`
      else if (mathSession) gameName = `Math Thinking (Nvl ${mathSession.difficulty_level || 1})`
      else if (iqSession) gameName = `IQ Matrices (Nvl ${iqSession.difficulty_level || 1})`
      return {
        icon: "🧠",
        label: gameName,
        category: "gym",
      }
    }
    if (path.includes("/dashboard") || path === "/") {
      return {
        icon: "📊",
        label: "Centro de Mando",
        category: "dashboard",
      }
    }
    return {
      icon: "💡",
      label: "Mentor Socrático",
      category: "general",
    }
  }, [location.pathname, paesActiveQuestion, paesActiveSubject, paesSubtopic, gameSession, mathSession, iqSession])

  // Contextual quick chips
  const quickSuggestions = useMemo(() => {
    if (contextMeta.category === "paes") {
      return [
        "¿Qué propiedad o axioma debo aplicar?",
        "¿Cómo desgloso este enunciado en partes simples?",
        "¿Qué me está pidiendo realmente la incógnita?",
        "Dame una pista de nivel 1 sin resolverlo",
      ]
    }
    if (contextMeta.category === "gym") {
      return [
        "¿Qué estrategia de chunking me recomiendas?",
        "¿Cómo reduzco la interferencia proactiva?",
        "Siento que saturé mi memoria de trabajo, ¿qué hago?",
      ]
    }
    return [
      "¿Cómo organizo una sesión deliberada hoy?",
      "¿Cómo convierto un error recurrente en una repetición mental?",
      "Explícame la diferencia entre práctica pasiva y deliberada",
    ]
  }, [contextMeta.category])

  const handleSubmit = async (e) => {
    e?.preventDefault()
    if (!inputText.trim() || coachLoading) return
    const textToSend = inputText
    setInputText("")
    await sendCoachMessage(textToSend)
  }

  const handleChipClick = async (chipText) => {
    if (coachLoading) return
    await sendCoachMessage(chipText)
  }

  if (!isCoachOpen) return null

  return (
    <div className="fixed inset-0 z-50 overflow-hidden" role="dialog" aria-modal="true" aria-label="Coach Cognitivo">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-xs transition-opacity duration-300"
        onClick={closeCoach}
        data-testid="coach-backdrop"
      />

      {/* Slide-over Drawer */}
      <div className="fixed inset-y-0 right-0 max-w-full flex pl-6 sm:pl-12">
        <aside className="w-screen max-w-md sm:max-w-lg bg-neutral-950/95 border-l border-white/[0.08] backdrop-blur-2xl shadow-2xl flex flex-col h-full transform transition ease-in-out duration-300">
          {/* Header */}
          <div className="px-5 py-4 border-b border-white/[0.06] flex items-center justify-between gap-3 bg-neutral-900/50">
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-emerald-500 to-teal-400 flex items-center justify-center text-black font-bold shadow-md shadow-emerald-500/20 shrink-0">
                <span>{contextMeta.icon}</span>
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-bold text-white tracking-tight truncate">
                    Coach Cognitivo
                  </h3>
                  <span className="flex h-2 w-2 relative shrink-0">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                  </span>
                </div>
                <div className="text-[11px] font-mono text-neutral-400 truncate flex items-center gap-1.5 mt-0.5">
                  <span className="text-neutral-500">Contexto:</span>
                  <span className="text-emerald-400 font-medium truncate">{contextMeta.label}</span>
                </div>
              </div>
            </div>

            {/* Actions: Clear & Close */}
            <div className="flex items-center gap-1.5 shrink-0">
              {coachMessages.length > 0 && (
                <button
                  type="button"
                  onClick={clearCoachMessages}
                  className="p-1.5 rounded-lg text-neutral-400 hover:text-neutral-200 hover:bg-white/[0.06] transition-colors text-xs flex items-center gap-1"
                  title="Limpiar conversación"
                  aria-label="Limpiar conversación"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              )}
              <button
                type="button"
                onClick={closeCoach}
                className="p-1.5 rounded-lg text-neutral-400 hover:text-white hover:bg-white/[0.08] transition-colors"
                title="Cerrar panel (Esc)"
                aria-label="Cerrar panel"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          {/* Socratic Zero-Spoilers Notice */}
          <div className="px-5 py-2 bg-emerald-950/20 border-b border-emerald-500/10 flex items-center justify-between text-[11px] text-emerald-300/80">
            <span className="flex items-center gap-1.5">
              <span>🛡️</span>
              <span>Método Socrático · Sin spoilers ni respuestas directas</span>
            </span>
            <span className="text-[10px] font-mono text-neutral-500">Esc para salir</span>
          </div>

          {/* Messages Area */}
          <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
            {coachMessages.length === 0 ? (
              <div className="h-full flex flex-col justify-center items-center text-center px-4 py-8">
                <div className="w-14 h-14 rounded-2xl bg-white/[0.03] border border-white/[0.08] flex items-center justify-center text-3xl mb-4 shadow-inner">
                  🧠
                </div>
                <h4 className="text-sm font-semibold text-neutral-200 mb-1.5">
                  Instructor Cognitivo Activo
                </h4>
                <p className="text-xs text-neutral-400 max-w-xs leading-relaxed mb-6">
                  Estoy observando tu pantalla. Te ayudaré a descomponer el problema y andamiar tu razonamiento paso a paso, sin darte la respuesta directa.
                </p>

                {/* Suggestions List */}
                <div className="w-full space-y-2">
                  <div className="text-[11px] font-mono font-medium text-neutral-500 uppercase tracking-wider text-left pl-1">
                    Preguntas sugeridas
                  </div>
                  {quickSuggestions.map((suggestion, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => handleChipClick(suggestion)}
                      disabled={coachLoading}
                      className="w-full text-left text-xs text-neutral-300 hover:text-white bg-white/[0.03] hover:bg-white/[0.07] border border-white/[0.06] hover:border-emerald-500/30 rounded-xl px-3.5 py-2.5 transition-all flex items-center justify-between group"
                    >
                      <span className="truncate pr-2">{suggestion}</span>
                      <span className="text-neutral-500 group-hover:text-emerald-400 transition-colors shrink-0">→</span>
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              coachMessages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex flex-col ${msg.role === "user" ? "items-end" : "items-start"}`}
                >
                  <div className="flex items-center gap-1.5 text-[10px] font-mono text-neutral-500 mb-1 px-1">
                    <span>{msg.role === "user" ? "Tú" : "Coach Socrático"}</span>
                    <span>·</span>
                    <span>
                      {new Date(msg.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </span>
                  </div>

                  <div
                    className={`rounded-2xl px-4 py-3 text-xs max-w-[92%] leading-relaxed ${
                      msg.role === "user"
                        ? "bg-emerald-600/20 border border-emerald-500/30 text-emerald-100 rounded-br-xs"
                        : "bg-neutral-900 border border-white/[0.08] text-neutral-200 rounded-bl-xs shadow-md"
                    }`}
                  >
                    {msg.role === "assistant" ? (
                      <MathRenderer text={msg.content} className="text-xs" />
                    ) : (
                      <p className="whitespace-pre-wrap">{msg.content}</p>
                    )}

                    {/* Metadata chips from Coach */}
                    {msg.concept_highlight && (
                      <div className="mt-2.5 pt-2 border-t border-white/[0.06] flex items-center gap-1.5 text-[11px] text-amber-300 font-mono">
                        <span className="shrink-0">🎯</span>
                        <span className="font-semibold">Concepto clave:</span>
                        <span className="truncate">{msg.concept_highlight}</span>
                      </div>
                    )}

                    {msg.suggested_action && (
                      <div className="mt-1.5 flex items-center gap-1.5 text-[11px] text-emerald-300 font-mono">
                        <span className="shrink-0">⚡</span>
                        <span className="font-semibold">Próximo paso:</span>
                        <span className="truncate">{msg.suggested_action}</span>
                      </div>
                    )}

                    {msg.consulted_document && (
                      <div className="mt-1.5 flex items-center gap-1.5 text-[11px] text-cyan-300 font-mono">
                        <span className="shrink-0">📖</span>
                        <span className="font-semibold">Fuente DEMRE:</span>
                        <span className="truncate">{msg.consulted_document}</span>
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}

            {/* Loading indicator */}
            {coachLoading && (
              <div className="flex items-center gap-2 text-xs text-neutral-400 bg-neutral-900/60 border border-white/[0.06] rounded-xl px-3.5 py-2.5 max-w-[80%]">
                <svg className="animate-spin h-3.5 w-3.5 text-emerald-400" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span>Razonando intervención pedagógica...</span>
              </div>
            )}

            {/* Error banner */}
            {coachError && (
              <div className="p-3 bg-red-950/30 border border-red-500/30 rounded-xl text-xs text-red-300 flex items-start gap-2">
                <span className="shrink-0">⚠️</span>
                <span>{coachError}</span>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Quick suggestions when history exists */}
          {coachMessages.length > 0 && !coachLoading && (
            <div className="px-5 py-2 border-t border-white/[0.04] bg-neutral-950/40 flex items-center gap-1.5 overflow-x-auto no-scrollbar">
              <span className="text-[10px] text-neutral-500 shrink-0">💡 Pistas:</span>
              {quickSuggestions.slice(0, 2).map((sug, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => handleChipClick(sug)}
                  className="shrink-0 text-[11px] text-neutral-400 hover:text-white bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.06] rounded-full px-2.5 py-1 transition-colors"
                >
                  {sug}
                </button>
              ))}
            </div>
          )}

          {/* Input & Form */}
          <div className="p-4 border-t border-white/[0.08] bg-neutral-900/60">
            <form onSubmit={handleSubmit} className="flex flex-col gap-2">
              <div className="relative flex items-center">
                <textarea
                  ref={inputRef}
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault()
                      handleSubmit(e)
                    }
                  }}
                  rows={2}
                  disabled={coachLoading}
                  placeholder="Pregúntale al coach (ej: ¿Qué propiedad uso acá?)..."
                  className="w-full bg-neutral-950 border border-white/[0.1] rounded-xl px-3.5 py-2.5 pr-12 text-xs text-neutral-100 placeholder-neutral-500 focus:outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/50 resize-none transition-all disabled:opacity-50"
                />
                <button
                  type="submit"
                  disabled={!inputText.trim() || coachLoading}
                  className="absolute right-2.5 bottom-2.5 p-2 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-black font-bold disabled:opacity-30 disabled:hover:bg-emerald-500 transition-all shadow-sm"
                  title="Enviar consulta"
                  aria-label="Enviar consulta"
                >
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M14 5l7 7m0 0l-7 7m7-7H3" />
                  </svg>
                </button>
              </div>

              <div className="flex items-center justify-between text-[10px] text-neutral-500 px-1">
                <span>Enter para enviar · Shift+Enter para nueva línea</span>
                <span className="font-mono">Peak Socratic AI</span>
              </div>
            </form>
          </div>
        </aside>
      </div>
    </div>
  )
}
