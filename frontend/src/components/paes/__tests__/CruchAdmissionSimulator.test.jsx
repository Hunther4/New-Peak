import React from "react"
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import { CruchAdmissionSimulator, getCareerUrl, UNIVERSITY_ADMISSION_URLS } from "../CruchAdmissionSimulator"
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

    expect((await screen.findAllByText(/Beauchef/i)).length).toBeGreaterThan(0)
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

  it("renders scope controls and grouped career optgroups", async () => {
    render(<CruchAdmissionSimulator />)

    await waitFor(() => {
      expect(api.paes.admission.getCareers).toHaveBeenCalled()
    })

    expect(screen.getByText(/Top \/ Alta Demanda/i)).toBeInTheDocument()
    expect(screen.getByText(/Catálogo Completo/i)).toBeInTheDocument()
    expect(screen.getByRole("combobox")).toBeInTheDocument()
  })

  it("renders 'Link de la carrera' link with target _blank and valid admission URL", async () => {
    render(<CruchAdmissionSimulator />)

    await waitFor(() => {
      expect(api.paes.admission.getCareers).toHaveBeenCalled()
    })

    const careerLink = await screen.findByRole("link", { name: /Link de la carrera/i })
    expect(careerLink).toBeInTheDocument()
    expect(careerLink).toHaveAttribute("target", "_blank")
    expect(careerLink).toHaveAttribute("rel", "noopener noreferrer")
    expect(careerLink).toHaveAttribute("href", "https://admision.uchile.cl/")
  })

  describe("getCareerUrl helper and fallbacks", () => {
    it("prioritizes career.url when explicitly defined", () => {
      expect(getCareerUrl({ url: "https://example.com/medicina", university_short: "UCH" })).toBe("https://example.com/medicina")
    })

    it("uses career.link when url is not present", () => {
      expect(getCareerUrl({ link: "https://example.com/carrera-link", university_short: "PUC" })).toBe("https://example.com/carrera-link")
    })

    it("resolves specific UdeC URL when code is present in catalogue", () => {
      expect(getCareerUrl({ code: "13086", university_short: "UdeC" })).toBe("https://admision.udec.cl/medicina/")
      expect(getCareerUrl({ code: "13080", university_short: "UdeC" })).toBe("https://admision.udec.cl/arquitectura/")
    })

    it("resolves intelligent fallback URLs for all CRUCH partner universities by shortcode", () => {
      expect(getCareerUrl({ university_short: "UdeC" })).toBe("https://admision.udec.cl/")
      expect(getCareerUrl({ university_short: "UTALCA" })).toBe("https://admision.utalca.cl/")
      expect(getCareerUrl({ university_short: "UCM" })).toBe("https://admision.ucm.cl/")
      expect(getCareerUrl({ university_short: "UA" })).toBe("https://admision.uautonoma.cl/")
      expect(getCareerUrl({ university_short: "UCH" })).toBe("https://admision.uchile.cl/")
      expect(getCareerUrl({ university_short: "PUC" })).toBe("https://admision.uc.cl/")
      expect(getCareerUrl({ university_short: "USACH" })).toBe("https://admision.usach.cl/")
      expect(getCareerUrl({ university_short: "UTFSM" })).toBe("https://usm.cl/")
      expect(getCareerUrl({ university_short: "UBB" })).toBe("https://admision.ubiobio.cl/")
      expect(getCareerUrl({ university_short: "UCSC" })).toBe("https://admision.ucsc.cl/")
    })

    it("resolves intelligent fallback by university name if shortcode is missing", () => {
      expect(getCareerUrl({ university: "Universidad de Concepción" })).toBe("https://admision.udec.cl/")
      expect(getCareerUrl({ university: "Pontificia Universidad Católica de Chile" })).toBe("https://admision.uc.cl/")
      expect(getCareerUrl({ university: "Universidad Técnica Federico Santa María" })).toBe("https://usm.cl/")
      expect(getCareerUrl({ university: "Universidad del Bío-Bío" })).toBe("https://admision.ubiobio.cl/")
    })

    it("falls back to demre.cl when career is empty or unknown", () => {
      expect(getCareerUrl(null)).toBe("https://demre.cl/")
      expect(getCareerUrl({ university: "Universidad Desconocida" })).toBe("https://demre.cl/")
    })
  })
})
