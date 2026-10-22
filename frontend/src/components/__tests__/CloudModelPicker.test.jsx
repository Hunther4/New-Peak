import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import CloudModelPicker from "../CloudModelPicker"
import { api } from "../../api/client"
import { useStore } from "../../store/store"

vi.mock("../../api/client", () => ({
  api: {
    models: {
      getKeys: vi.fn(),
      setKey: vi.fn(),
      getAvailableForKey: vi.fn(),
      select: vi.fn(),
      selectAuto: vi.fn(),
    },
  },
}))

vi.mock("../../store/store", () => ({
  useStore: vi.fn(),
}))

const storeState = () => ({
  selectedModel: { auto: true },
  selectModel: vi.fn().mockResolvedValue(undefined),
  selectModelAuto: vi.fn().mockResolvedValue(undefined),
  fetchAiStatus: vi.fn(),
})

beforeEach(() => {
  vi.clearAllMocks()
  useStore.mockReturnValue(storeState())
})

describe("CloudModelPicker", () => {
  it("fetches available models for the default provider (groq)", async () => {
    api.models.getAvailableForKey.mockResolvedValue([
      { model_id: "llama-3.1-8b-instant", name: "Llama 3.1 8B" },
      { model_id: "qwen/qwen3-32b", name: "Qwen3 32B" },
    ])
    render(<CloudModelPicker />)

    await waitFor(() =>
      expect(api.models.getAvailableForKey).toHaveBeenCalledWith("groq")
    )
    expect(await screen.findByText("Llama 3.1 8B")).toBeInTheDocument()
    expect(screen.getByText("qwen/qwen3-32b")).toBeInTheDocument()
  })

  it("refetches when switching provider tab", async () => {
    api.models.getAvailableForKey.mockResolvedValue([
      { model_id: "deepseek-v3.2", name: "DeepSeek V3.2" },
    ])
    render(<CloudModelPicker />)

    await waitFor(() =>
      expect(api.models.getAvailableForKey).toHaveBeenCalledWith("groq")
    )
    fireEvent.click(screen.getByRole("button", { name: /General Compute/ }))

    await waitFor(() =>
      expect(api.models.getAvailableForKey).toHaveBeenCalledWith("generalcompute")
    )
    expect(await screen.findByText("DeepSeek V3.2")).toBeInTheDocument()
  })

  it("selecting a model + save posts the /select shape", async () => {
    api.models.getAvailableForKey.mockResolvedValue([
      { model_id: "deepseek-v3.2", name: "DeepSeek V3.2" },
    ])
    const store = storeState()
    useStore.mockReturnValue(store)
    render(<CloudModelPicker />)

    fireEvent.click(await screen.findByTestId("picker-model-deepseek-v3.2"))
    fireEvent.click(screen.getByRole("button", { name: "Guardar selección" }))

    await waitFor(() =>
      expect(store.selectModel).toHaveBeenCalledWith(
        "DeepSeek V3.2",
        "groq",
        "deepseek-v3.2"
      )
    )
    expect(store.selectModelAuto).not.toHaveBeenCalled()
    expect(store.fetchAiStatus).toHaveBeenCalled()
  })

  it("defaults to auto and save calls selectModelAuto", async () => {
    api.models.getAvailableForKey.mockResolvedValue([
      { model_id: "m1", name: "Model One" },
    ])
    const store = storeState()
    useStore.mockReturnValue(store)
    render(<CloudModelPicker />)

    await screen.findByText("Model One")
    fireEvent.click(screen.getByRole("button", { name: "Guardar selección" }))

    await waitFor(() => expect(store.selectModelAuto).toHaveBeenCalledTimes(1))
    expect(store.selectModel).not.toHaveBeenCalled()
  })

  it("uses model_id as display name when name is missing", async () => {
    api.models.getAvailableForKey.mockResolvedValue([
      { model_id: "gpt-oss-120b" },
    ])
    const store = storeState()
    useStore.mockReturnValue(store)
    render(<CloudModelPicker />)

    fireEvent.click(await screen.findByTestId("picker-model-gpt-oss-120b"))
    fireEvent.click(screen.getByRole("button", { name: "Guardar selección" }))

    await waitFor(() =>
      expect(store.selectModel).toHaveBeenCalledWith(
        "gpt-oss-120b",
        "groq",
        "gpt-oss-120b"
      )
    )
  })

  it("shows the backend error when the key is missing or rejected", async () => {
    api.models.getAvailableForKey.mockRejectedValue(
      new Error("No hay API key configurada para groq")
    )
    render(<CloudModelPicker />)

    expect(await screen.findByTestId("picker-error")).toHaveTextContent(
      "No hay API key configurada para groq"
    )
  })

  it("shows empty state when the provider returns no models", async () => {
    api.models.getAvailableForKey.mockResolvedValue([])
    render(<CloudModelPicker />)

    expect(
      await screen.findByText("Sin modelos disponibles para esta key.")
    ).toBeInTheDocument()
  })
})
