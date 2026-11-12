import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"

const mockNavigate = vi.fn()

vi.mock("react-router", () => ({
  useNavigate: () => mockNavigate,
}))

vi.mock("../../../store/store", () => ({
  useStore: vi.fn(),
}))

import { useStore } from "../../../store/store"
import OptimalDailyAction from "../OptimalDailyAction"

const REVIEW_ITEM = {
  slug: "algebra-lineal",
  subtopic_id: 42,
  subtopic_name: "Algebra lineal",
  subject_code: "M1",
}

function renderWith({ queue = [], list = [], subject = "M1" } = {}) {
  useStore.mockReturnValue({
    paesSubtopicsList: list,
    paesFsrsStatus: { capped_review_queue: queue },
    paesActiveSubject: subject,
    skills: [],
  })
  return render(<OptimalDailyAction />)
}

describe("OptimalDailyAction", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("con repaso FSRS vencido muestra el título pedagógico y el botón al Temario", () => {
    renderWith({ queue: [REVIEW_ITEM] })

    expect(screen.getByText(/Refuerzo FSRS: revisa los temas pendientes de M1/)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /Revisar temario/i })).toBeInTheDocument()
    expect(screen.getByText("Repasos pendientes")).toBeInTheDocument()
  })

  it("el título usa la materia del elemento vencido, no la materia activa", () => {
    renderWith({ queue: [{ ...REVIEW_ITEM, subject_code: "LECTURA" }], subject: "M1" })
    expect(screen.getByText(/Refuerzo FSRS: revisa los temas pendientes de LECTURA/)).toBeInTheDocument()
    expect(screen.queryByText(/temas pendientes de M1/)).not.toBeInTheDocument()
  })

  it("sin FSRS pero con baja maestría en la materia activa manda al Temario de esa materia", () => {
    renderWith({
      list: [{ slug: "t1", subject_code: "M1", attempts: 2, mastery: 0.3 }],
      subject: "M1",
    })
    expect(screen.getByText(/Zona de desarrollo próximo: refuerza temas de M1/)).toBeInTheDocument()
    expect(screen.getByText("ZDP Óptima")).toBeInTheDocument()
  })

  it("la ZDP no sugiere electivas sin tocar (se acota a la materia activa)", () => {
    renderWith({
      list: [{ slug: "t1", subject_code: "CIENCIAS", attempts: 2, mastery: 0.1 }],
      subject: "M1",
    })
    // Sin intentos en M1, no sugiere ZDP
    expect(screen.queryByText(/Zona de desarrollo próximo/)).not.toBeInTheDocument()
  })

  it("sin FSRS ni ZDP, prioriza el ensayo de la materia activa directamente a /paes", () => {
    renderWith({ queue: [], list: [], subject: "M1" })

    expect(screen.getByText(/Ensayo de M1: inicia tu práctica oficial/i)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /Iniciar ensayo/i })).toBeInTheDocument()
    expect(screen.getByText("Ensayo del día")).toBeInTheDocument()

    // No debe redirigir a gimnasio cognitivo como primera opción
    expect(screen.queryByText(/Hoy toca memoria de trabajo/i)).not.toBeInTheDocument()

    // Al hacer clic, navega directamente a /paes
    fireEvent.click(screen.getByRole("button", { name: /Iniciar ensayo/i }))
    expect(mockNavigate).toHaveBeenCalledWith("/paes")
  })
})
