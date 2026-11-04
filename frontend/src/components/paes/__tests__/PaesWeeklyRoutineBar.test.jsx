import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import { PaesWeeklyRoutineBar } from "../PaesWeeklyRoutineBar"
import { api } from "../../../api/client"

vi.mock("../../../api/client", () => ({
  api: {
    paes: {
      getRoutine: vi.fn(),
      updateRoutine: vi.fn(),
    },
  },
}))

const CACHE_KEY = "peak_paes_weekly_routine"

// The component reads the wall clock to decide which day is "today". Pinning it
// keeps every assertion below independent of the day the suite happens to run.
const FIXED_TODAY = "monday"

const DEFAULT_ROUTINE = {
  monday: "M1",
  tuesday: "LECTURA",
  wednesday: "M1",
  thursday: "CIENCIAS",
  friday: "M1",
  saturday: "M1",
  sunday: "REST",
}

describe("PaesWeeklyRoutineBar - saving the weekly routine", () => {
  beforeEach(() => {
    vi.resetAllMocks()
    window.localStorage.clear()
    api.paes.getRoutine.mockResolvedValue({ routine: { ...DEFAULT_ROUTINE } })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("edita directo al desplegar: tocar un día y elegir su materia guarda sin modal ni botón de configurar", async () => {
    const acknowledged = { ...DEFAULT_ROUTINE, tuesday: "CIENCIAS" }
    api.paes.updateRoutine.mockResolvedValue({ routine: acknowledged })
    render(<PaesWeeklyRoutineBar onStartSession={vi.fn()} todayKey={FIXED_TODAY} />)
    await waitFor(() => expect(api.paes.getRoutine).toHaveBeenCalled())

    // No hay modal ni botón de configurar en la versión minimalista
    expect(screen.queryByText("Personalizar Rutina Semanal")).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /Personalizar/i })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /Configurar/i })).not.toBeInTheDocument()

    // Seleccionar el día martes y cambiar su materia a CIENCIAS
    fireEvent.click(screen.getByText("Mar"))
    fireEvent.click(screen.getByTestId("subject-chip-CIENCIAS"))

    await waitFor(() =>
      expect(api.paes.updateRoutine).toHaveBeenCalledWith(acknowledged)
    )
    await waitFor(() =>
      expect(screen.getByTestId("routine-save-status")).toHaveTextContent("Guardado")
    )
  })

  it("muestra error visible y nunca presenta la rutina como guardada cuando el servidor rechaza", async () => {
    api.paes.updateRoutine.mockRejectedValue(new Error("Network unreachable"))
    render(<PaesWeeklyRoutineBar onStartSession={vi.fn()} todayKey={FIXED_TODAY} />)
    await waitFor(() => expect(api.paes.getRoutine).toHaveBeenCalled())

    fireEvent.click(screen.getByText("Mar"))
    fireEvent.click(screen.getByTestId("subject-chip-CIENCIAS"))

    const alert = await screen.findByRole("alert")
    expect(alert).toHaveTextContent(/No se pudo guardar/i)
    expect(screen.getByTestId("routine-save-status")).toHaveTextContent("Falló el guardado")
  })

  it("ofrece reintentar y guarda cuando el servidor confirma", async () => {
    const acknowledged = { ...DEFAULT_ROUTINE, tuesday: "CIENCIAS" }
    api.paes.updateRoutine
      .mockRejectedValueOnce(new Error("Network unreachable"))
      .mockResolvedValueOnce({ routine: acknowledged })
    render(<PaesWeeklyRoutineBar onStartSession={vi.fn()} todayKey={FIXED_TODAY} />)
    await waitFor(() => expect(api.paes.getRoutine).toHaveBeenCalled())

    fireEvent.click(screen.getByText("Mar"))
    fireEvent.click(screen.getByTestId("subject-chip-CIENCIAS"))
    await screen.findByRole("alert")

    fireEvent.click(screen.getByRole("button", { name: /Reintentar/i }))

    await waitFor(() =>
      expect(screen.getByTestId("routine-save-status")).toHaveTextContent("Guardado")
    )
    expect(screen.queryByRole("alert")).not.toBeInTheDocument()
  })

  it("escribe la caché local con la rutina confirmada por el servidor", async () => {
    const setItem = vi.spyOn(Storage.prototype, "setItem")
    const acknowledged = { ...DEFAULT_ROUTINE, tuesday: "CIENCIAS" }
    api.paes.updateRoutine.mockResolvedValue({ routine: acknowledged })
    render(<PaesWeeklyRoutineBar onStartSession={vi.fn()} todayKey={FIXED_TODAY} />)
    await waitFor(() => expect(api.paes.getRoutine).toHaveBeenCalled())

    fireEvent.click(screen.getByText("Mar"))
    fireEvent.click(screen.getByTestId("subject-chip-CIENCIAS"))

    await waitFor(() =>
      expect(setItem).toHaveBeenCalledWith(CACHE_KEY, JSON.stringify(acknowledged))
    )
    expect(screen.getByTestId("routine-save-status")).toHaveTextContent("Guardado")
  })

  it("usa la caché cuando el servidor no responde", async () => {
    api.paes.getRoutine.mockRejectedValue(new Error("offline"))
    window.localStorage.setItem(
      CACHE_KEY,
      JSON.stringify({ ...DEFAULT_ROUTINE, monday: "HISTORIA" })
    )
    render(<PaesWeeklyRoutineBar onStartSession={vi.fn()} todayKey={FIXED_TODAY} />)

    await waitFor(() => expect(screen.getByText("HISTORIA")).toBeInTheDocument())
  })

  it("muestra 7 tarjetas legibles con el día de hoy destacado", async () => {
    render(<PaesWeeklyRoutineBar onStartSession={vi.fn()} todayKey={FIXED_TODAY} />)
    await waitFor(() => expect(api.paes.getRoutine).toHaveBeenCalled())

    expect(screen.getByText("Lun")).toBeInTheDocument()
    expect(screen.getByText("Mar")).toBeInTheDocument()
    expect(screen.getByText("Mié")).toBeInTheDocument()
    expect(screen.getByText("Jue")).toBeInTheDocument()
    expect(screen.getByText("Vie")).toBeInTheDocument()
    expect(screen.getByText("Sáb")).toBeInTheDocument()
    expect(screen.getByText("Dom")).toBeInTheDocument()
    expect(screen.getByText("Hoy")).toBeInTheDocument()
    // Sin "Módulo del día" ni botón brillante al desplegar
    expect(screen.queryByText(/Módulo del día/i)).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /Iniciar sesión de hoy/i })).not.toBeInTheDocument()
  })

  it("muestra el editor directo con las materias del día seleccionado", async () => {
    render(<PaesWeeklyRoutineBar onStartSession={vi.fn()} todayKey={FIXED_TODAY} />)
    await waitFor(() => expect(api.paes.getRoutine).toHaveBeenCalled())

    expect(screen.getByTestId("subject-chip-M1")).toBeInTheDocument()
    expect(screen.getByTestId("subject-chip-LECTURA")).toBeInTheDocument()
    expect(screen.getByTestId("subject-chip-CIENCIAS")).toBeInTheDocument()
    expect(screen.getByTestId("subject-chip-M2")).toBeInTheDocument()
    expect(screen.getByTestId("subject-chip-HISTORIA")).toBeInTheDocument()
    expect(screen.getByTestId("subject-chip-REST")).toBeInTheDocument()
  })

  it("se puede retraer y desplegar", async () => {
    render(<PaesWeeklyRoutineBar onStartSession={vi.fn()} todayKey={FIXED_TODAY} />)
    await waitFor(() => expect(api.paes.getRoutine).toHaveBeenCalled())

    expect(screen.getByText("Lun")).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: /Retraer/i }))
    expect(screen.getByText("(Retraída)")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /Desplegar/i })).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: /Desplegar/i }))
    expect(screen.queryByText("(Retraída)")).not.toBeInTheDocument()
  })

  it("se puede ocultar y restaurar", async () => {
    const onDismiss = vi.fn()
    render(<PaesWeeklyRoutineBar onStartSession={vi.fn()} onDismiss={onDismiss} todayKey={FIXED_TODAY} />)
    await waitFor(() => expect(api.paes.getRoutine).toHaveBeenCalled())

    fireEvent.click(screen.getByRole("button", { name: /Eliminar/i }))
    expect(onDismiss).toHaveBeenCalledTimes(1)
    expect(screen.getByText("Rutina semanal oculta de la pantalla")).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: /Mostrar Rutina/i }))
    expect(screen.getByText("Tu Rutina Semanal")).toBeInTheDocument()
  })
})
