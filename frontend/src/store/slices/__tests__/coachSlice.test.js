import { describe, it, expect, vi, beforeEach } from "vitest"
import { useStore } from "../../store"
import { api } from "../../../api/client"

vi.mock("../../../api/client", () => ({
  api: {
    coach: {
      chat: vi.fn(),
    },
  },
}))

describe("coachSlice", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useStore.getState().__unsafe_reset__()
  })

  it("toggles and closes coach drawer", () => {
    expect(useStore.getState().isCoachOpen).toBe(false)
    useStore.getState().toggleCoach()
    expect(useStore.getState().isCoachOpen).toBe(true)
    useStore.getState().closeCoach()
    expect(useStore.getState().isCoachOpen).toBe(false)
  })

  it("sends message and appends response with context", async () => {
    const mockReply = {
      reply: "Piensa en el Teorema de Pitágoras.",
      concept_highlight: "Geometría Euclidiana",
      suggested_action: "Dibuja el triángulo rectángulo",
    }
    api.coach.chat.mockResolvedValueOnce(mockReply)

    useStore.setState({
      paesActiveSubject: "M1",
      paesActiveQuestion: {
        stem: "¿Cuál es la hipotenusa?",
        subject: "M1",
        subtopic: "Geometría",
        options: [{ key: "A", text: "5" }],
      },
    })

    await useStore.getState().sendCoachMessage("¿Cómo calculo el lado faltante?")

    const messages = useStore.getState().coachMessages
    expect(messages.length).toBe(2)
    expect(messages[0].role).toBe("user")
    expect(messages[0].content).toBe("¿Cómo calculo el lado faltante?")
    expect(messages[1].role).toBe("assistant")
    expect(messages[1].content).toBe("Piensa en el Teorema de Pitágoras.")
    expect(messages[1].concept_highlight).toBe("Geometría Euclidiana")

    // Check payload passed to api.coach.chat
    expect(api.coach.chat).toHaveBeenCalledWith(
      expect.objectContaining({
        message: "¿Cómo calculo el lado faltante?",
        context_type: "paes",
        active_question: expect.objectContaining({
          stem: "¿Cuál es la hipotenusa?",
          subject: "M1",
          subtopic: "Geometría",
        }),
      })
    )
  })

  it("handles api error gracefully", async () => {
    api.coach.chat.mockRejectedValueOnce(new Error("Network timeout"))

    await useStore.getState().sendCoachMessage("Hola")

    expect(useStore.getState().coachError).toBe("Network timeout")
    expect(useStore.getState().coachLoading).toBe(false)
  })
})
