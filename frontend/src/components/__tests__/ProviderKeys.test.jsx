import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent, waitFor, within } from "@testing-library/react"
import ProviderKeys from "../ProviderKeys"
import { api } from "../../api/client"

vi.mock("../../api/client", () => ({
  api: {
    models: {
      getKeys: vi.fn(),
      setKey: vi.fn(),
      getAvailableForKey: vi.fn(),
    },
  },
}))

const UNCONFIGURED = {
  groq: { configured: false, masked: null },
  openrouter: { configured: false, masked: null },
  generalcompute: { configured: false, masked: null },
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe("ProviderKeys", () => {
  it("renders all three providers with 'sin key' when unconfigured", async () => {
    api.models.getKeys.mockResolvedValue(UNCONFIGURED)
    render(<ProviderKeys />)

    expect(await screen.findByTestId("provider-key-groq")).toBeInTheDocument()
    expect(screen.getByTestId("provider-key-openrouter")).toBeInTheDocument()
    expect(screen.getByTestId("provider-key-generalcompute")).toBeInTheDocument()
    expect(screen.getAllByText("sin key")).toHaveLength(3)
    expect(api.models.getKeys).toHaveBeenCalledTimes(1)
  })

  it("shows masked key when configured, never the full key", async () => {
    api.models.getKeys.mockResolvedValue({
      ...UNCONFIGURED,
      groq: { configured: true, masked: "gsk_…9999" },
    })
    render(<ProviderKeys />)

    expect(await screen.findByText("gsk_…9999")).toBeInTheDocument()
    expect(screen.getAllByText("sin key")).toHaveLength(2) // las otras dos
  })

  it("saves a typed key via PUT and clears the input", async () => {
    api.models.getKeys.mockResolvedValue(UNCONFIGURED)
    api.models.setKey.mockResolvedValue({
      status: "success",
      provider: "groq",
      configured: true,
      masked: "gsk_…abcd",
    })
    render(<ProviderKeys />)

    const row = within(await screen.findByTestId("provider-key-groq"))
    const input = row.getByLabelText("API key de Groq")
    fireEvent.change(input, { target: { value: "gsk_new-secret-key-1234" } })
    fireEvent.click(row.getByRole("button", { name: "Guardar" }))

    await waitFor(() =>
      expect(api.models.setKey).toHaveBeenCalledWith("groq", "gsk_new-secret-key-1234")
    )
    await waitFor(() => expect(screen.getByText("gsk_…abcd")).toBeInTheDocument())
    expect(input.value).toBe("")
  })

  it("does not call setKey when input is empty", async () => {
    api.models.getKeys.mockResolvedValue(UNCONFIGURED)
    render(<ProviderKeys />)

    const row = within(await screen.findByTestId("provider-key-groq"))
    const saveButton = row.getByRole("button", { name: "Guardar" })
    expect(saveButton).toBeDisabled()
    fireEvent.click(saveButton)
    expect(api.models.setKey).not.toHaveBeenCalled()
  })

  it("clears a configured key via empty string PUT", async () => {
    api.models.getKeys.mockResolvedValue({
      ...UNCONFIGURED,
      openrouter: { configured: true, masked: "sk-o…7890" },
    })
    api.models.setKey.mockResolvedValue({
      status: "success",
      provider: "openrouter",
      configured: false,
      masked: null,
    })
    render(<ProviderKeys />)

    const row = within(await screen.findByTestId("provider-key-openrouter"))
    const clearButton = row.getByRole("button", { name: "Limpiar" })
    fireEvent.click(clearButton)

    await waitFor(() =>
      expect(api.models.setKey).toHaveBeenCalledWith("openrouter", "")
    )
    await waitFor(() => expect(row.getByText("sin key")).toBeInTheDocument())
  })

  it("shows the provider error inline when save fails", async () => {
    api.models.getKeys.mockResolvedValue(UNCONFIGURED)
    api.models.setKey.mockRejectedValue(new Error("Invalid API key"))
    render(<ProviderKeys />)

    const row = within(await screen.findByTestId("provider-key-generalcompute"))
    const input = row.getByLabelText("API key de General Compute")
    fireEvent.change(input, { target: { value: "bad-key-123456" } })
    fireEvent.click(row.getByRole("button", { name: "Guardar" }))

    expect(await row.findByRole("alert")).toHaveTextContent("Invalid API key")
  })
})
