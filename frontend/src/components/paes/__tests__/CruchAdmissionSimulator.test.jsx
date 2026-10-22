import React from "react"
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import { CruchAdmissionSimulator } from "../CruchAdmissionSimulator"
import { api } from "../../../api/client"

vi.mock("../../../api/client", () => ({
  api: {
    paes: {
      admission: {
        getCareers: vi.fn(),
        simulate: vi.fn(),
      },
    },
  },
}))

describe("CruchAdmissionSimulator Component", () => {
  const mockCareers = [
    {
      id: "ing-civil-uch",
      name: "Ingeniería Civil - Plan Común",
      university: "Universidad de Chile",
      university_short: "UCH",
      campus: "Beauchef",
      area: "Ingeniería",
      vacantes: 800,
      weights: { nem: 0.1, ranking: 0.2, lectura: 0.1, m1: 0.35, m2: 0.15, ciencias: 0.1, historia: 0 },
      cutoffs: { 2024: 890.6, 2025: 893.2, 2026: 896.5 },
      requires_m2: true,
    },
    {
      id: "medicina-puc",
      name: "Medicina",
      university: "Pontificia Universidad Católica de Chile",
      university_short: "PUC",
      campus: "Casa Central",
      area: "Salud",
      vacantes: 120,
      weights: { nem: 0.1, ranking: 0.2, lectura: 0.15, m1: 0.2, m2: 0.1, ciencias: 0.25, historia: 0 },
      cutoffs: { 2024: 955.5, 2025: 958.2, 2026: 959.8 },
      requires_m2: true,
    },
  ]

  const mockSimulation = {
    career_id: "ing-civil-uch",
    career_name: "Ingeniería Civil - Plan Común",
    university: "Universidad de Chile",
    university_short: "UCH",
    target_cutoff: 896.5,
    weighted_score: 910.25,
    probability: 88.5,
    category: "Segura",
    status_message: "Alta certeza de selección.",
    confidence_interval_95: [898.0, 922.5],
    weighted_gap: -13.75,
    gap_breakdown: {
      m1: {
        subject_code: "M1",
        subject_name: "Competencia Matemática 1",
        weight_percent: 35,
        current_score: 800,
        target_score: 800,
        net_points_needed: 0,
        current_raw_items: 50,
        target_raw_items: 50,
        additional_correct_needed: 0,
        is_achievable_alone: true,
      },
    },
    balanced_plan: [],
    all_careers_summary: [
      {
        career_id: "ing-civil-uch",
        career_name: "Ingeniería Civil - Plan Común",
        university_short: "UCH",
        weighted_score: 910.25,
        probability: 88.5,
        category: "Segura",
      },
    ],
  }

  beforeEach(() => {
    vi.clearAllMocks()
    api.paes.admission.getCareers.mockResolvedValue({ careers: mockCareers })
    api.paes.admission.simulate.mockResolvedValue({ simulation: mockSimulation })
  })

  it("renders header and loads CRUCH careers catalog", async () => {
    render(<CruchAdmissionSimulator />)

    expect(screen.getByText(/Simulador de Admisión & Probabilidad CRUCH/i)).toBeInTheDocument()

    await waitFor(() => {
      expect(api.paes.admission.getCareers).toHaveBeenCalledTimes(1)
    })

    expect(await screen.findByText(/Beauchef/i)).toBeInTheDocument()
  })

  it("renders live probability bar and admission verdict", async () => {
    render(<CruchAdmissionSimulator />)

    await waitFor(() => {
      expect(api.paes.admission.simulate).toHaveBeenCalled()
    })

    expect(await screen.findByText("88.5%")).toBeInTheDocument()
    expect(screen.getAllByText("Segura").length).toBeGreaterThan(0)
    expect(screen.getByText(/Alta certeza de selección/i)).toBeInTheDocument()
  })
})
