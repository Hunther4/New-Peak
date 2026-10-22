import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("react-router", () => ({
  useNavigate: () => vi.fn(),
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

function renderWithQueue(queue) {
  useStore.mockReturnValue({
    paesSubtopicsList: [],
    paesFsrsStatus: { capped_review_queue: queue },
    skills: [],
  })
  return render(<OptimalDailyAction />)
}

function subtitle() {
  return screen.getByTestId("optimal-daily-action-subtitle")
}

describe("OptimalDailyAction - FSRS retention claim", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("states the real projected retention of the top review item instead of an unmeasured threshold claim", () => {
    renderWithQueue([{ ...REVIEW_ITEM, projected_retention: 0.62 }])

    expect(subtitle()).toHaveTextContent("62%")
    expect(subtitle()).not.toHaveTextContent(/below/i)
  })

  it("does not claim the item falls short of the target when its retention is above 85%", () => {
    renderWithQueue([{ ...REVIEW_ITEM, projected_retention: 0.91 }])

    expect(subtitle()).toHaveTextContent("91%")
    expect(subtitle()).not.toHaveTextContent(/below/i)
    expect(subtitle()).toHaveTextContent("85%")
  })

  it("only asks for reinforcement when the retention is really under the target", () => {
    renderWithQueue([{ ...REVIEW_ITEM, projected_retention: 0.8 }])

    expect(subtitle()).toHaveTextContent("80%")
    expect(subtitle()).toHaveTextContent(/needs reinforcement/i)
  })

  it("does not ask for reinforcement when the retention reaches the target", () => {
    renderWithQueue([{ ...REVIEW_ITEM, projected_retention: 0.85 }])

    expect(subtitle()).toHaveTextContent("85%")
    expect(subtitle()).not.toHaveTextContent(/needs reinforcement/i)
  })

  it("falls back to projected_r when projected_retention is missing", () => {
    renderWithQueue([{ ...REVIEW_ITEM, projected_r: 0.74 }])

    expect(subtitle()).toHaveTextContent("74%")
    expect(subtitle()).toHaveTextContent(/needs reinforcement/i)
  })

  it("states the fact without inventing a retention number when the item has no retention value", () => {
    renderWithQueue([{ ...REVIEW_ITEM }])

    expect(subtitle()).not.toHaveTextContent(/%/)
    expect(subtitle()).toHaveTextContent(/no retention estimate/i)
  })
})
