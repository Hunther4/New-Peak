import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("react-router", () => ({
  useNavigate: () => vi.fn(),
}))

vi.mock("../../store/store", () => ({
  useStore: Object.assign(vi.fn(), { getState: vi.fn(), setState: vi.fn() }),
}))

vi.mock("../../api/client", () => ({
  api: {
    paes: {
      getRoutine: vi.fn().mockResolvedValue({ routine: {} }),
      updateRoutine: vi.fn().mockResolvedValue({}),
    },
  },
}))

import { useStore } from "../../store/store"
import Dashboard from "../Dashboard"

function createMockState(overrides = {}) {
  return {
    // PAES
    paesSubtopicsList: [],
    paesFsrsStatus: { capped_review_queue: [] },
    paesActiveSubject: "M1",
    setPaesActiveSubject: vi.fn(),
    fetchPaesSubtopics: vi.fn(),
    fetchPaesFsrsStatus: vi.fn(),
    // Skills/Sessions
    skills: [],
    sessions: [],
    summary: null,
    groupedSummary: [],
    timeline: [],
    loading: false,
    error: null,
    // Profile
    profile: null,
    profileLoading: false,
    // Books
    books: [],
    booksLoading: false,
    isIndexing: false,
    indexingProgress: 0,
    // Mental
    mentalReps: [],
    challenges: [],
    pendingChallenges: 0,
    generatingRep: false,
    generatingChallenge: false,
    // AI
    ai_mode: "local",
    available_models: [],
    best_model: null,
    selectedModel: { auto: true },
    // Actions
    clearError: vi.fn(),
    fetchSkills: vi.fn(),
    fetchSummary: vi.fn(),
    fetchTimeline: vi.fn(),
    fetchMentalReps: vi.fn(),
    fetchChallenges: vi.fn(),
    fetchBooksStatus: vi.fn(),
    fetchAiStatus: vi.fn(),
    ...overrides,
  }
}

describe("Dashboard", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders without crashing", () => {
    useStore.mockReturnValue(createMockState())
    useStore.getState.mockReturnValue(createMockState())
    render(<Dashboard />)
    expect(screen.getByText("Tu Rutina Semanal")).toBeInTheDocument()
  })

  it("muestra la acción diaria con el título honesto", () => {
    useStore.mockReturnValue(createMockState({
      paesFsrsStatus: { capped_review_queue: [{ subject_code: "M1" }] },
    }))
    useStore.getState.mockReturnValue(createMockState())
    render(<Dashboard />)
    expect(screen.getByText(/Presiona el botón hoy y revisa todos los temas de M1/)).toBeInTheDocument()
  })

  it("muestra las secciones Desafíos Deliberados y Registro de Auditoría", () => {
    useStore.mockReturnValue(createMockState())
    useStore.getState.mockReturnValue(createMockState())
    render(<Dashboard />)
    expect(screen.getByText("Desafíos Deliberados")).toBeInTheDocument()
    expect(screen.getByText("Registro de Auditoría")).toBeInTheDocument()
  })
})
