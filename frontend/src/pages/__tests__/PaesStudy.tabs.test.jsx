import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { MemoryRouter } from "react-router"

const { storeState } = vi.hoisted(() => ({ storeState: {} }))

vi.mock("../../store/store", () => ({
  useStore: () => storeState,
}))

vi.mock("../../api/client", () => ({
  api: {
    paes: {
      getRoutine: vi.fn().mockResolvedValue({ routine: {} }),
      updateRoutine: vi.fn().mockResolvedValue({}),
      getParametricQuestion: vi.fn().mockResolvedValue(null),
    },
  },
}))

import PaesStudy from "../PaesStudy"

function renderStudy(entry = "/paes") {
  return render(
    <MemoryRouter initialEntries={[entry]}>
      <PaesStudy />
    </MemoryRouter>
  )
}

describe("PaesStudy - hub tabs", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    Object.assign(storeState, {
      paesSessionId: null,
      paesSubtopic: null,
      paesQuestions: [],
      paesCurrentIndex: 0,
      paesActiveQuestion: null,
      paesSelectedOption: null,
      paesConfidence: 3,
      paesLastResult: null,
      paesFsrsStatus: {
        due_for_review_count: 1,
        capped_review_queue: [],
        subject_code: "M1",
      },
      paesSubtopicsList: [],
      paesSocraticHints: [],
      paesLoading: false,
      paesError: null,
      paesExamActive: false,
      paesExamResults: null,
      paesActiveSubject: "M1",
      paesErrorNotebook: { total_errors: 0, by_subject: {}, by_mistake_cause: {}, items: [] },
      fetchPaesSubjects: vi.fn(),
      setPaesActiveSubject: vi.fn(),
      fetchPaesFsrsStatus: vi.fn(),
      fetchPaesSubtopics: vi.fn(),
      fetchPaesErrorNotebook: vi.fn(),
      loadErrorVault: vi.fn(),
      startRevengeSession: vi.fn(),
      startPaesSession: vi.fn(),
      startPaesExam: vi.fn(),
      selectPaesOption: vi.fn(),
      setPaesConfidence: vi.fn(),
      submitPaesAttempt: vi.fn(),
      nextPaesQuestion: vi.fn(),
      requestSocraticHint: vi.fn(),
      resetPaesSession: vi.fn(),
      exitPaesExam: vi.fn(),
    })
  })

  it("keeps the exams tab as the default tab", () => {
    renderStudy()

    expect(screen.getByText("Tu Rutina Semanal de 1-Clic")).toBeInTheDocument()
    expect(screen.queryByText("Generador Paramétrico SymPy")).not.toBeInTheDocument()
    expect(screen.queryByText("Motor FSRS v4.5")).not.toBeInTheDocument()
  })

  it("exposes the parametric generator tab and renders its block when selected", () => {
    renderStudy()
    expect(screen.queryByText("Generador Paramétrico SymPy")).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: /Parametric Generator/i }))

    expect(screen.getByText("Generador Paramétrico SymPy")).toBeInTheDocument()
  })

  it("exposes the FSRS status tab and renders the retention widget when selected", () => {
    renderStudy()
    expect(screen.queryByText("Motor FSRS v4.5")).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: /FSRS Memory Status/i }))

    expect(screen.getByText("Motor FSRS v4.5")).toBeInTheDocument()
  })

  it("still opens the parametric block through the ?tab= query parameter", () => {
    renderStudy("/paes?tab=parametric")

    expect(screen.getByText("Generador Paramétrico SymPy")).toBeInTheDocument()
  })

  it("still opens the FSRS widget through the ?tab= query parameter", () => {
    renderStudy("/paes?tab=fsrs")

    expect(screen.getByText("Motor FSRS v4.5")).toBeInTheDocument()
  })
})
