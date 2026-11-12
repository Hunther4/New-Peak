import React from "react"
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent, act } from "@testing-library/react"
import { PaesExamRunner } from "../PaesExamRunner"
import { PaesExamResults } from "../PaesExamResults"
import { useStore } from "../../../store/store"

describe("PaesExamRunner", () => {
  beforeEach(() => {
    useStore.setState({
      paesQuestions: [
        {
          id: "q1",
          stem: "Resuelve $2x + 4 = 10$",
          options: [
            { key: "A", content: "$x = 3$" },
            { key: "B", content: "$x = 2$" },
            { key: "C", content: "$x = 4$" },
            { key: "D", content: "$x = 5$" },
          ],
        },
        {
          id: "q2",
          stem: "¿Cuál es el área de un cuadrado de lado 4?",
          options: [
            { key: "A", content: "16" },
            { key: "B", content: "8" },
            { key: "C", content: "12" },
            { key: "D", content: "20" },
          ],
        },
      ],
      paesCurrentIndex: 0,
      paesActiveQuestion: {
        id: "q1",
        stem: "Resuelve $2x + 4 = 10$",
        options: [
          { key: "A", content: "$x = 3$" },
          { key: "B", content: "$x = 2$" },
          { key: "C", content: "$x = 4$" },
          { key: "D", content: "$x = 5$" },
        ],
      },
      paesExamAnswers: {},
      paesExamFlags: [],
      paesExamTimeLimitMinutes: 32,
      paesLoading: false,
    })
  })

  it("renders exam header and question content", () => {
    render(<PaesExamRunner />)
    expect(screen.getByText(/Simulacro Oficial DEMRE M1/i)).toBeInTheDocument()
    expect(screen.getByText(/Pregunta 1 de 2/i)).toBeInTheDocument()
  })

  it("selects an option when clicked", () => {
    render(<PaesExamRunner />)
    const optA = screen.getByText(/x = 3/i)
    fireEvent.click(optA)
    const state = useStore.getState()
    expect(state.paesExamAnswers["q1"]?.selectedOption).toBe("A")
  })

  it("renders the pacing bar for active item", () => {
    render(<PaesExamRunner />)
    const pacingBar = screen.getByTestId("paes-pacing-bar")
    expect(pacingBar).toBeInTheDocument()
    expect(screen.getByText(/Tiempo en esta pregunta/i)).toBeInTheDocument()
    expect(screen.getByText(/\/ 03:00 sugerido/i)).toBeInTheDocument()
  })

  it("updates pacing bar to amber warning when exceeding 3 minutes", () => {
    vi.useFakeTimers()
    render(<PaesExamRunner />)

    // Advance timers past 3 minutes (185 seconds)
    act(() => {
      vi.advanceTimersByTime(185000)
    })

    expect(screen.getByText(/Tiempo sugerido excedido: ¡Gestiona tu ritmo DEMRE!/i)).toBeInTheDocument()
    vi.useRealTimers()
  })

  it("toggles sound mute via the header switch", () => {
    render(<PaesExamRunner />)
    const soundToggle = screen.getByTestId("exam-sound-toggle")
    expect(soundToggle).toBeInTheDocument()

    // Click to mute
    fireEvent.click(soundToggle)
    expect(localStorage.getItem("peak_sound_muted")).toBe("true")

    // Click to unmute
    fireEvent.click(soundToggle)
    expect(localStorage.getItem("peak_sound_muted")).toBe("false")
  })

  it("toggles auto-advance via the header switch", () => {
    render(<PaesExamRunner />)
    const toggle = screen.getByTestId("exam-auto-advance-toggle")
    expect(toggle).toBeInTheDocument()
    expect(toggle).toHaveAttribute("aria-pressed", "true")

    // Click to disable
    fireEvent.click(toggle)
    expect(toggle).toHaveAttribute("aria-pressed", "false")
    expect(localStorage.getItem("paes_exam_auto_advance")).toBe("false")

    // Click to re-enable
    fireEvent.click(toggle)
    expect(toggle).toHaveAttribute("aria-pressed", "true")
    expect(localStorage.getItem("paes_exam_auto_advance")).toBe("true")
  })

  it("auto-advances to next question after 250ms when an option is selected", () => {
    vi.useFakeTimers()
    render(<PaesExamRunner />)

    expect(screen.getByText(/Pregunta 1 de 2/i)).toBeInTheDocument()

    const optA = screen.getByText(/x = 3/i)
    fireEvent.click(optA)

    expect(useStore.getState().paesExamAnswers["q1"]?.selectedOption).toBe("A")

    act(() => {
      vi.advanceTimersByTime(200)
    })
    expect(useStore.getState().paesCurrentIndex).toBe(0)

    act(() => {
      vi.advanceTimersByTime(60)
    })
    expect(useStore.getState().paesCurrentIndex).toBe(1)

    vi.useRealTimers()
  })

  it("does not auto-advance when auto-advance toggle is disabled", () => {
    vi.useFakeTimers()
    render(<PaesExamRunner />)

    const toggle = screen.getByTestId("exam-auto-advance-toggle")
    fireEvent.click(toggle)

    const optA = screen.getByText(/x = 3/i)
    fireEvent.click(optA)

    act(() => {
      vi.advanceTimersByTime(300)
    })
    expect(useStore.getState().paesCurrentIndex).toBe(0)

    vi.useRealTimers()
  })

  it("does not auto-advance on the last question", () => {
    vi.useFakeTimers()
    useStore.setState({
      paesCurrentIndex: 1,
      paesActiveQuestion: {
        id: "q2",
        stem: "¿Cuál es el área de un cuadrado de lado 4?",
        options: [
          { key: "A", content: "16" },
          { key: "B", content: "8" },
        ],
      },
    })
    render(<PaesExamRunner />)

    const optA = screen.getByText(/16/i)
    fireEvent.click(optA)

    act(() => {
      vi.advanceTimersByTime(300)
    })
    expect(useStore.getState().paesCurrentIndex).toBe(1)

    vi.useRealTimers()
  })

  it("resets window scroll on question change", () => {
    const scrollToSpy = vi.spyOn(window, "scrollTo")
    render(<PaesExamRunner />)

    expect(scrollToSpy).toHaveBeenCalledWith({ top: 0, behavior: "instant" })
  })

  it("applies responsive max-height constraints to exercise images", () => {
    useStore.setState({
      paesActiveQuestion: {
        id: "q_img",
        stem: "Pregunta con imagen",
        image_url: "https://example.com/demo.png",
        options: [
          { key: "A", content: "Opcion A" },
          { key: "B", content: "Opcion B" },
        ],
      },
    })
    render(<PaesExamRunner />)

    const img = screen.getByRole("img", { name: /Pregunta q_img/i })
    expect(img).toHaveClass("max-h-[36vh]")
    expect(img).toHaveClass("sm:max-h-[44vh]")
  })

  it("finalizes exam and stores results without error", async () => {
    const mockFinalize = vi.fn().mockResolvedValue({
      total_questions: 2,
      correct_count: 2,
      demre: { estimated_score: 1000 },
    })
    const { api } = await import("../../../api/client")
    api.paes = { ...api.paes, finalizeExam: mockFinalize }

    useStore.setState({
      paesSessionId: "test-sess-123",
      paesQuestions: [{ id: "q1" }, { id: "q2" }],
      paesExamAnswers: { q1: { selectedOption: "A", timeSpentSeconds: 10 } },
      paesActiveSubject: "M1",
      paesExamActive: true,
    })

    const results = await useStore.getState().finalizePaesExam()
    expect(mockFinalize).toHaveBeenCalledWith(
      "test-sess-123",
      expect.any(Array),
      "M1"
    )
    expect(results).toBeDefined()
    expect(useStore.getState().paesExamResults).toEqual(results)
    expect(useStore.getState().paesExamActive).toBe(false)
  })
})

describe("PaesExamResults", () => {
  beforeEach(() => {
    useStore.setState({
      paesExamResults: {
        total_questions: 15,
        correct_count: 12,
        incorrect_count: 2,
        unanswered_count: 1,
        accuracy_pct: 80,
        total_time_seconds: 1800,
        avg_time_per_question: 120,
        demre: {
          estimated_score: 723,
          estimated_range_str: "698 - 748 pts",
          percentile_approx: 84.5,
        },
        ejes_breakdown: [
          { name: "Números", total: 4, correct: 3, percentage: 75 },
          { name: "Álgebra y Funciones", total: 5, correct: 4, percentage: 80 },
        ],
        review: [
          {
            question_id: "q1",
            stem: "¿Cuánto es 2 + 2?",
            options: [{ key: "A", content: "4", is_correct: true }],
            selected_option: "A",
            correct_option: "A",
            is_correct: true,
            is_unanswered: false,
            time_spent_seconds: 30,
            eje_name: "Números",
            subtopic_name: "Operaciones",
          },
        ],
      },
    })
  })

  it("renders DEMRE estimated score and quick stats", () => {
    render(<PaesExamResults onNewExam={() => {}} onBackToStudy={() => {}} />)
    expect(screen.getByText("723")).toBeInTheDocument()
    expect(screen.getByText(/698 - 748 pts/i)).toBeInTheDocument()
    expect(screen.getByText(/Resultado Oficial DEMRE M1/i)).toBeInTheDocument()
  })
})
