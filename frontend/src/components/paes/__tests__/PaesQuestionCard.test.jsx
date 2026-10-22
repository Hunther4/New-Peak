import React from "react"
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { PaesQuestionCard } from "../PaesQuestionCard"
import * as soundEffects from "../../../utils/soundEffects"

vi.mock("../../../utils/soundEffects", () => ({
  playClickSound: vi.fn(),
  playSelectTap: vi.fn(),
  playSuccessSound: vi.fn(),
  playSuccessChime: vi.fn(),
  playErrorSound: vi.fn(),
  playErrorTone: vi.fn(),
  playStreakSound: vi.fn(),
  playStreakCelebration: vi.fn(),
  isSoundMuted: vi.fn(() => false),
  setSoundMuted: vi.fn(),
  toggleSoundMute: vi.fn(),
  playHaptic: vi.fn(),
}))

describe("PaesQuestionCard", () => {
  const dummyQuestion = {
    id: "q101",
    stem: "¿Cuánto es 5 + 5?",
    options: [
      { key: "A", content: "8" },
      { key: "B", content: "10" },
      { key: "C", content: "12" },
      { key: "D", content: "15" },
    ],
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders question stem and options", () => {
    render(
      <PaesQuestionCard
        question={dummyQuestion}
        selectedOption={null}
        onSelectOption={vi.fn()}
      />
    )
    expect(screen.getByText(/5 \+ 5/i)).toBeInTheDocument()
    expect(screen.getByText("10")).toBeInTheDocument()
  })

  it("plays click sound when an option is selected", () => {
    const onSelectMock = vi.fn()
    render(
      <PaesQuestionCard
        question={dummyQuestion}
        selectedOption={null}
        onSelectOption={onSelectMock}
      />
    )
    const optB = screen.getByText("10")
    fireEvent.click(optB)

    expect(soundEffects.playClickSound).toHaveBeenCalled()
    expect(onSelectMock).toHaveBeenCalledWith("B")
  })

  it("plays success sound upon correct answer", () => {
    const { rerender } = render(
      <PaesQuestionCard
        question={dummyQuestion}
        selectedOption="B"
        lastResult={null}
      />
    )

    rerender(
      <PaesQuestionCard
        question={dummyQuestion}
        selectedOption="B"
        lastResult={{ is_correct: true, correct_option: "B" }}
      />
    )

    expect(soundEffects.playSuccessSound).toHaveBeenCalled()
    expect(soundEffects.playErrorSound).not.toHaveBeenCalled()
  })

  it("plays error sound upon incorrect answer", () => {
    const { rerender } = render(
      <PaesQuestionCard
        question={dummyQuestion}
        selectedOption="A"
        lastResult={null}
      />
    )

    rerender(
      <PaesQuestionCard
        question={dummyQuestion}
        selectedOption="A"
        lastResult={{ is_correct: false, correct_option: "B" }}
      />
    )

    expect(soundEffects.playErrorSound).toHaveBeenCalled()
    expect(soundEffects.playSuccessSound).not.toHaveBeenCalled()
  })

  it("plays streak sound when streak count reaches 3 or more", () => {
    const { rerender } = render(
      <PaesQuestionCard
        question={dummyQuestion}
        selectedOption="B"
        lastResult={null}
      />
    )

    rerender(
      <PaesQuestionCard
        question={dummyQuestion}
        selectedOption="B"
        lastResult={{ is_correct: true, correct_option: "B", streak_count: 3 }}
      />
    )

    expect(soundEffects.playStreakSound).toHaveBeenCalledWith(3)
  })
})
