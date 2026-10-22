import { api } from "../../api/client"

export const createCoachSlice = (set, get) => ({
  isCoachOpen: false,
  coachMessages: [],
  coachLoading: false,
  coachError: null,

  toggleCoach: () => set((state) => ({ isCoachOpen: !state.isCoachOpen })),
  openCoach: () => set({ isCoachOpen: true }),
  closeCoach: () => set({ isCoachOpen: false }),

  clearCoachMessages: () => set({ coachMessages: [], coachError: null }),

  sendCoachMessage: async (text) => {
    const trimmed = text?.trim()
    if (!trimmed || get().coachLoading) return

    const userMsgId = `msg-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
    const userMessage = {
      id: userMsgId,
      role: "user",
      content: trimmed,
      timestamp: Date.now(),
    }

    // Actualizamos optimísticamente la lista de mensajes
    set((state) => ({
      coachMessages: [...state.coachMessages, userMessage],
      coachLoading: true,
      coachError: null,
    }))

    try {
      const state = get()
      const pathname = typeof window !== "undefined" ? window.location?.pathname || "" : ""

      // 1. Detección de tipo de contexto
      let contextType = "general"
      let activeQuestion = null
      let gameContext = null

      if (state.paesActiveQuestion || pathname.includes("/paes")) {
        contextType = "paes"
        if (state.paesActiveQuestion) {
          const q = state.paesActiveQuestion
          activeQuestion = {
            stem: q.stem || q.question_text || "",
            subject: q.subject || state.paesActiveSubject || "M1",
            subtopic: q.subtopic || state.paesSubtopic?.name || "General",
            options: Array.isArray(q.options)
              ? q.options.map((opt) => ({
                  key: opt.key || opt.id || "",
                  text: opt.text || opt.label || "",
                }))
              : [],
          }
        }
      } else if (pathname.includes("/gym")) {
        contextType = "gym"
        if (state.gameSession) {
          gameContext = {
            game: "Dual N-Back",
            level: state.gameSession.current_n || 2,
            accuracy: state.gameSession.accuracy || null,
          }
        } else if (state.mathSession) {
          gameContext = {
            game: "Math Thinking",
            level: state.mathSession.difficulty_level || 1,
            score: state.mathSession.score || null,
          }
        } else if (state.iqSession) {
          gameContext = {
            game: "IQ Matrix Practice",
            level: state.iqSession.difficulty_level || 1,
          }
        }
      } else if (pathname.includes("/dashboard") || pathname === "/") {
        contextType = "dashboard"
      }

      // 2. Historial formateado (últimos 6 turnos antes del actual)
      const history = (state.coachMessages || [])
        .slice(-6)
        .map((m) => ({
          role: m.role,
          content: m.content,
        }))

      // 3. Petición a la API
      const response = await api.coach.chat({
        message: trimmed,
        context_type: contextType,
        active_question: activeQuestion,
        game_context: gameContext,
        history,
      })

      const assistantMsgId = `coach-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
      const assistantMessage = {
        id: assistantMsgId,
        role: "assistant",
        content: response.reply,
        concept_highlight: response.concept_highlight || null,
        suggested_action: response.suggested_action || null,
        consulted_document: response.consulted_document || null,
        timestamp: Date.now(),
      }

      set((s) => ({
        coachMessages: [...s.coachMessages, assistantMessage],
        coachLoading: false,
      }))

      return response
    } catch (err) {
      set({
        coachError: err.message || "Error al comunicarse con el coach cognitivo.",
        coachLoading: false,
      })
    }
  },
})
