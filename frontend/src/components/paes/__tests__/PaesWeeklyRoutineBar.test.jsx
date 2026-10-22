import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { render, screen, fireEvent, waitFor, within } from "@testing-library/react"
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

/** Opens the Tuesday picker and picks the given subject label. */
async function pickSubjectForTuesday(label) {
  const dayLabel = screen.getByText("Mar")
  fireEvent.click(dayLabel)
  // Scope the subject query to Tuesday's own cell: the same subject label can
  // also appear outside the picker (e.g. in the "today" badge), which makes a
  // page-wide query ambiguous depending on the day of the week.
  const dayCell = dayLabel.closest("div.relative")
  fireEvent.click(within(dayCell).getByText(label))
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

  it("shows a visible error and never presents the routine as saved when the server rejects the change", async () => {
    api.paes.updateRoutine.mockRejectedValue(new Error("Network unreachable"))
    render(<PaesWeeklyRoutineBar onStartSession={vi.fn()} todayKey={FIXED_TODAY} />)
    await waitFor(() => expect(api.paes.getRoutine).toHaveBeenCalled())

    await pickSubjectForTuesday("Ciencias")

    const alert = await screen.findByRole("alert")
    expect(alert).toHaveTextContent(/not saved/i)
    expect(screen.getByTestId("routine-save-status")).toHaveTextContent("Save failed")
    expect(screen.queryByText("Saved")).not.toBeInTheDocument()
    // The change never reached the server, so it must not be presented as applied:
    // Tuesday keeps its previous subject and only the default Thursday keeps CIENCIAS.
    expect(screen.getByText("LECTURA")).toBeInTheDocument()
    expect(screen.getAllByText("CIENCIAS")).toHaveLength(1)
  })

  it("offers a retry that saves the routine once the server acknowledges it", async () => {
    const acknowledged = { ...DEFAULT_ROUTINE, tuesday: "CIENCIAS" }
    api.paes.updateRoutine
      .mockRejectedValueOnce(new Error("Network unreachable"))
      .mockResolvedValueOnce({ routine: acknowledged })
    render(<PaesWeeklyRoutineBar onStartSession={vi.fn()} todayKey={FIXED_TODAY} />)
    await waitFor(() => expect(api.paes.getRoutine).toHaveBeenCalled())

    await pickSubjectForTuesday("Ciencias")
    await screen.findByRole("alert")

    fireEvent.click(screen.getByRole("button", { name: /retry/i }))

    await waitFor(() =>
      expect(screen.getByTestId("routine-save-status")).toHaveTextContent("Saved")
    )
    expect(screen.queryByRole("alert")).not.toBeInTheDocument()
    expect(screen.getAllByText("CIENCIAS")).toHaveLength(2)
  })

  it("still saves the routine when the local cache cannot be written and shows no error", async () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {})
    const setItem = vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("QuotaExceededError")
    })
    api.paes.updateRoutine.mockResolvedValue({ routine: { ...DEFAULT_ROUTINE, tuesday: "CIENCIAS" } })
    render(<PaesWeeklyRoutineBar onStartSession={vi.fn()} todayKey={FIXED_TODAY} />)
    await waitFor(() => expect(api.paes.getRoutine).toHaveBeenCalled())

    await pickSubjectForTuesday("Ciencias")

    await waitFor(() =>
      expect(screen.getByTestId("routine-save-status")).toHaveTextContent("Saved")
    )
    expect(screen.queryByRole("alert")).not.toBeInTheDocument()
    expect(api.paes.updateRoutine).toHaveBeenCalledTimes(1)
    expect(setItem).toHaveBeenCalled()
    expect(warn).toHaveBeenCalled()
  })

  it("writes the local cache with the server acknowledged routine", async () => {
    const setItem = vi.spyOn(Storage.prototype, "setItem")
    const acknowledged = { ...DEFAULT_ROUTINE, tuesday: "CIENCIAS" }
    api.paes.updateRoutine.mockResolvedValue({ routine: acknowledged })
    render(<PaesWeeklyRoutineBar onStartSession={vi.fn()} todayKey={FIXED_TODAY} />)
    await waitFor(() => expect(api.paes.getRoutine).toHaveBeenCalled())

    await pickSubjectForTuesday("Ciencias")

    await waitFor(() =>
      expect(setItem).toHaveBeenCalledWith(CACHE_KEY, JSON.stringify(acknowledged))
    )
    expect(screen.getByTestId("routine-save-status")).toHaveTextContent("Saved")
  })

  it("falls back to the cached routine when the routine cannot be read from the server", async () => {
    api.paes.getRoutine.mockRejectedValue(new Error("offline"))
    window.localStorage.setItem(
      CACHE_KEY,
      JSON.stringify({ ...DEFAULT_ROUTINE, monday: "HISTORIA" })
    )
    render(<PaesWeeklyRoutineBar onStartSession={vi.fn()} todayKey={FIXED_TODAY} />)

    await waitFor(() => expect(screen.getByText("HISTORIA")).toBeInTheDocument())
  })

  it("reports the save as in flight while the server request is pending", async () => {
    let resolveUpdate
    api.paes.updateRoutine.mockImplementation(
      () => new Promise((resolve) => { resolveUpdate = resolve })
    )
    render(<PaesWeeklyRoutineBar onStartSession={vi.fn()} todayKey={FIXED_TODAY} />)
    await waitFor(() => expect(api.paes.getRoutine).toHaveBeenCalled())

    await pickSubjectForTuesday("Ciencias")

    await waitFor(() =>
      expect(screen.getByTestId("routine-save-status")).toHaveTextContent("Saving")
    )

    resolveUpdate({ routine: { ...DEFAULT_ROUTINE, tuesday: "CIENCIAS" } })

    await waitFor(() =>
      expect(screen.getByTestId("routine-save-status")).toHaveTextContent("Saved")
    )
  })

  it("opens the customization modal when clicking the customizable button and allows saving a preset", async () => {
    const ubbPreset = {
      monday: "M1",
      tuesday: "LECTURA",
      wednesday: "M1",
      thursday: "CIENCIAS",
      friday: "M1",
      saturday: "M1",
      sunday: "REST",
    }
    api.paes.updateRoutine.mockResolvedValue({ routine: ubbPreset })
    render(<PaesWeeklyRoutineBar onStartSession={vi.fn()} todayKey={FIXED_TODAY} />)
    await waitFor(() => expect(api.paes.getRoutine).toHaveBeenCalled())

    // Click the Customizable button
    fireEvent.click(screen.getByTestId("routine-save-status"))

    // Modal is opened
    expect(screen.getByText("Personalizar Rutina Semanal")).toBeInTheDocument()
    expect(screen.getByText("Enfoque M1 UBB (Recomendado)")).toBeInTheDocument()

    // Click preset and save
    fireEvent.click(screen.getByText("Enfoque M1 UBB (Recomendado)"))
    fireEvent.click(screen.getByRole("button", { name: /Guardar Rutina/i }))

    await waitFor(() =>
      expect(api.paes.updateRoutine).toHaveBeenCalledWith(ubbPreset, 1)
    )
  })

  it("can be collapsed and expanded through the Retraer and Desplegar buttons", async () => {
    render(<PaesWeeklyRoutineBar onStartSession={vi.fn()} todayKey={FIXED_TODAY} />)
    await waitFor(() => expect(api.paes.getRoutine).toHaveBeenCalled())

    // Currently expanded: days of week are visible
    expect(screen.getByText("Lun")).toBeInTheDocument()

    // Click Retraer
    fireEvent.click(screen.getByRole("button", { name: /Retraer/i }))
    expect(screen.getByText("(Retraída)")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /Desplegar/i })).toBeInTheDocument()

    // Click Desplegar
    fireEvent.click(screen.getByRole("button", { name: /Desplegar/i }))
    expect(screen.queryByText("(Retraída)")).not.toBeInTheDocument()
  })

  it("can be dismissed and restored through Eliminar and Mostrar Rutina buttons", async () => {
    const onDismiss = vi.fn()
    render(<PaesWeeklyRoutineBar onStartSession={vi.fn()} onDismiss={onDismiss} todayKey={FIXED_TODAY} />)
    await waitFor(() => expect(api.paes.getRoutine).toHaveBeenCalled())

    // Click Eliminar
    fireEvent.click(screen.getByRole("button", { name: /Eliminar/i }))
    expect(onDismiss).toHaveBeenCalledTimes(1)
    expect(screen.getByText("Rutina semanal oculta de la pantalla")).toBeInTheDocument()

    // Click Mostrar Rutina to restore
    fireEvent.click(screen.getByRole("button", { name: /Mostrar Rutina/i }))
    expect(screen.getByText("Tu Rutina Semanal de 1-Clic")).toBeInTheDocument()
  })

  it("honours the injected today instead of the wall clock", async () => {
    api.paes.getRoutine.mockResolvedValue({ routine: { ...DEFAULT_ROUTINE } })

    // Pick a day that is guaranteed to differ from the real one, so the
    // assertion proves the injected value wins over new Date().getDay().
    const realDay = [
      "sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday",
    ][new Date().getDay()]
    const otherDay = realDay === "thursday" ? "monday" : "thursday"
    const expectedLabel = otherDay === "thursday" ? "Ciencias" : "M1 Matemática"

    render(<PaesWeeklyRoutineBar onStartSession={vi.fn()} todayKey={otherDay} />)
    await waitFor(() => expect(api.paes.getRoutine).toHaveBeenCalled())

    expect(screen.getByText("Módulo del día:")).toBeInTheDocument()
    expect(screen.getAllByText(expectedLabel).length).toBeGreaterThan(0)
  })
})
