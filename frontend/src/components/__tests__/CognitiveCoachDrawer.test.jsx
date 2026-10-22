import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import { MemoryRouter } from "react-router"
import CognitiveCoachDrawer from "../layout/CognitiveCoachDrawer"
import { useStore } from "../../store/store"

describe("CognitiveCoachDrawer", () => {
  beforeEach(() => {
    useStore.getState().__unsafe_reset__()
  })

  it("does not render when isCoachOpen is false", () => {
    useStore.setState({ isCoachOpen: false })
    const { container } = render(
      <MemoryRouter>
        <CognitiveCoachDrawer />
      </MemoryRouter>
    )
    expect(container.firstChild).toBeNull()
  })

  it("renders drawer and header when isCoachOpen is true", () => {
    useStore.setState({ isCoachOpen: true })
    render(
      <MemoryRouter>
        <CognitiveCoachDrawer />
      </MemoryRouter>
    )

    expect(screen.getByText("Coach Cognitivo")).toBeInTheDocument()
    expect(screen.getByText(/Método Socrático/i)).toBeInTheDocument()
    expect(screen.getByRole("textbox")).toBeInTheDocument()
  })

  it("displays PAES context chip when paesActiveQuestion is present", () => {
    useStore.setState({
      isCoachOpen: true,
      paesActiveSubject: "M1",
      paesActiveQuestion: {
        stem: "¿Cuál es el valor de x en $2x = 8$?",
        subject: "M1",
        subtopic: "Ecuaciones",
      },
    })

    render(
      <MemoryRouter>
        <CognitiveCoachDrawer />
      </MemoryRouter>
    )

    expect(screen.getByText(/PAES M1 · Ecuaciones/i)).toBeInTheDocument()
  })

  it("closes when close button is clicked", () => {
    useStore.setState({ isCoachOpen: true })
    render(
      <MemoryRouter>
        <CognitiveCoachDrawer />
      </MemoryRouter>
    )

    const closeBtn = screen.getByLabelText("Cerrar panel")
    fireEvent.click(closeBtn)

    expect(useStore.getState().isCoachOpen).toBe(false)
  })

  it("renders messages and quick suggestions", () => {
    useStore.setState({
      isCoachOpen: true,
      coachMessages: [
        {
          id: "1",
          role: "user",
          content: "¿Cómo abordo este ítem?",
          timestamp: Date.now(),
        },
        {
          id: "2",
          role: "assistant",
          content: "Comienza despejando la incógnita $x$.",
          concept_highlight: "Ecuaciones Lineales",
          suggested_action: "Resta 4 en ambos lados",
          timestamp: Date.now(),
        },
      ],
    })

    render(
      <MemoryRouter>
        <CognitiveCoachDrawer />
      </MemoryRouter>
    )

    expect(screen.getByText("¿Cómo abordo este ítem?")).toBeInTheDocument()
    expect(screen.getByText(/Comienza despejando la incógnita/i)).toBeInTheDocument()
    expect(screen.getByText("Ecuaciones Lineales")).toBeInTheDocument()
    expect(screen.getByText("Resta 4 en ambos lados")).toBeInTheDocument()
  })
})
