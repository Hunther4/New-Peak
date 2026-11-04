import React, { useState, useEffect, useMemo, useCallback } from "react"
import { api } from "../../api/client"
import { gradeFromNem, nemFromGrade } from "../../utils/nemScale"

export const UNIVERSITY_ADMISSION_URLS = {
  UdeC: "https://admision.udec.cl/",
  UTALCA: "https://admision.utalca.cl/",
  UCM: "https://admision.ucm.cl/",
  UA: "https://admision.uautonoma.cl/",
  UCH: "https://admision.uchile.cl/",
  PUC: "https://admision.uc.cl/",
  USACH: "https://admision.usach.cl/",
  UTFSM: "https://usm.cl/",
  UBB: "https://admision.ubiobio.cl/",
  UCSC: "https://admision.ucsc.cl/",
}

export const UDEC_CAREER_URLS = {
  "13001": "https://admision.udec.cl/licenciatura-en-quimica-quimico/",
  "13002": "https://admision.udec.cl/licenciatura-en-matematica/",
  "13003": "https://admision.udec.cl/ingenieria-civil-matematica/",
  "13004": "https://admision.udec.cl/quimico-a-analista/",
  "13008": "https://admision.udec.cl/ingenieria-forestal/",
  "13009": "https://admision.udec.cl/ingenieria-civil-agricola/",
  "13012": "https://admision.udec.cl/bioingenieria/",
  "13013": "https://admision.udec.cl/biologia-marina/",
  "13014": "https://admision.udec.cl/biologia/",
  "13015": "https://admision.udec.cl/geologia/",
  "13016": "https://admision.udec.cl/ingenieria-en-biotecnologia-marina-y-acuicultura/",
  "13018": "https://admision.udec.cl/geografia/",
  "13019": "https://admision.udec.cl/ingenieria-comercial/",
  "13025": "https://admision.udec.cl/trabajo-social/",
  "13026": "https://admision.udec.cl/antropologia/",
  "13027": "https://admision.udec.cl/educacion-parvularia/",
  "13031": "https://admision.udec.cl/periodismo/",
  "13036": "https://admision.udec.cl/pedagogia-en-ciencias-naturales-y-fisica/",
  "13037": "https://admision.udec.cl/pedagogia-en-ciencias-naturales-y-quimica/",
  "13039": "https://admision.udec.cl/pedagogia-en-educacion-musical/",
  "13040": "https://admision.udec.cl/pedagogia-en-historia-y-geografia/",
  "13041": "https://admision.udec.cl/pedagogia-en-espanol/",
  "13042": "https://admision.udec.cl/pedagogia-en-filosofia/",
  "13043": "https://admision.udec.cl/ingenieria-en-conservacion-de-recursos-naturales/",
  "13044": "https://admision.udec.cl/ingenieria-ambiental-chillan/",
  "13046": "https://admision.udec.cl/ciencias-fisicas/",
  "13048": "https://admision.udec.cl/bioquimica/",
  "13049": "https://admision.udec.cl/quimica-y-farmacia/",
  "13050": "https://admision.udec.cl/nutricion-y-dietetica/",
  "13052": "https://admision.udec.cl/bachillerato-en-humanidades/",
  "13054": "https://admision.udec.cl/artes-visuales/",
  "13055": "https://admision.udec.cl/astronomia/",
  "13056": "https://admision.udec.cl/geofisica/",
  "13058": "https://admision.udec.cl/traduccion-interpretacion-en-idiomas-extranjeros/",
  "13059": "https://admision.udec.cl/licenciatura-en-historia/",
  "13060": "https://admision.udec.cl/teatro/",
  "13061": "https://admision.udec.cl/ingenieria-ambiental/",
  "13062": "https://admision.udec.cl/ingenieria-civil-biomedica/",
  "13064": "https://admision.udec.cl/ingenieria-civil-en-telecomunicaciones/",
  "13065": "https://admision.udec.cl/ingenieria-estadistica/",
  "13066": "https://admision.udec.cl/ingenieria-civil-aeroespacial/",
  "13067": "https://admision.udec.cl/psicologia/",
  "13068": "https://admision.udec.cl/ingenieria-civil-primer-ano-comun/",
  "13069": "https://admision.udec.cl/ingenieria-civil/",
  "13070": "https://admision.udec.cl/ingenieria-civil-electrica/",
  "13071": "https://admision.udec.cl/ingenieria-civil-electronica/",
  "13072": "https://admision.udec.cl/ingenieria-civil-industrial/",
  "13073": "https://admision.udec.cl/ingenieria-civil-informatica/",
  "13074": "https://admision.udec.cl/ingenieria-civil-mecanica/",
  "13075": "https://admision.udec.cl/ingenieria-civil-metalurgica/",
  "13076": "https://admision.udec.cl/ingenieria-civil-quimica/",
  "13077": "https://admision.udec.cl/sociologia/",
  "13080": "https://admision.udec.cl/arquitectura/",
  "13081": "https://admision.udec.cl/tecnologia-medica/",
  "13082": "https://admision.udec.cl/fonoaudiologia/",
  "13083": "https://admision.udec.cl/kinesiologia/",
  "13086": "https://admision.udec.cl/medicina/",
  "13087": "https://admision.udec.cl/enfermeria/",
  "13088": "https://admision.udec.cl/obstetricia-y-puericultura/",
  "13091": "https://admision.udec.cl/odontologia/",
  "13093": "https://admision.udec.cl/ingenieria-geomatica/",
  "13101": "https://admision.udec.cl/pedagogia-en-educacion-fisica/",
  "13102": "https://admision.udec.cl/ingenieria-civil-de-minas/",
  "13107": "https://admision.udec.cl/pedagogia-en-artes-visuales/",
  "13112": "https://admision.udec.cl/pedagogia-en-espanol-los-angeles/",
  "13114": "https://admision.udec.cl/bachillerato-en-ciencias-e-innovacion/",
}

export function getCareerUrl(career) {
  if (!career) return "https://demre.cl/"
  if (career.url) return career.url
  if (career.link) return career.link

  if (career.code && UDEC_CAREER_URLS[career.code]) {
    return UDEC_CAREER_URLS[career.code]
  }
  if (career.code === "29028" || career.id === "ingenieria-civil-en-automatizacion-ubb") {
    return "https://ubiobio.cl/admision/Todas_las_Carreras/9/Ingenieria_Civil_en_Automatizacion/"
  }

  const shortCode = career.university_short
  if (shortCode && UNIVERSITY_ADMISSION_URLS[shortCode]) {
    return UNIVERSITY_ADMISSION_URLS[shortCode]
  }

  const uni = (career.university || "").toLowerCase()
  if (uni.includes("concepción") || uni.includes("udec")) return UNIVERSITY_ADMISSION_URLS.UdeC
  if (uni.includes("talca") || uni.includes("utalca")) return UNIVERSITY_ADMISSION_URLS.UTALCA
  if (uni.includes("maule") || uni.includes("ucm")) return UNIVERSITY_ADMISSION_URLS.UCM
  if (uni.includes("autónoma") || uni.includes("autonoma")) return UNIVERSITY_ADMISSION_URLS.UA
  if (uni.includes("santiago de chile") || uni.includes("usach")) return UNIVERSITY_ADMISSION_URLS.USACH
  if (uni.includes("santa maría") || uni.includes("santa maria") || uni.includes("utfsm") || uni.includes("usm")) return UNIVERSITY_ADMISSION_URLS.UTFSM
  if (uni.includes("bío-bío") || uni.includes("bio-bio") || uni.includes("biobío") || uni.includes("ubb")) return UNIVERSITY_ADMISSION_URLS.UBB
  if (uni.includes("santísima") || uni.includes("santisima") || uni.includes("ucsc")) return UNIVERSITY_ADMISSION_URLS.UCSC
  if (uni.includes("católica de chile") || uni.includes("puc") || (uni.includes("católica") && uni.includes("pontificia"))) return UNIVERSITY_ADMISSION_URLS.PUC
  if (uni.includes("chile")) return UNIVERSITY_ADMISSION_URLS.UCH

  return "https://demre.cl/"
}

export function CruchAdmissionSimulator() {
  const [careers, setCareers] = useState([])
  const [loadingCareers, setLoadingCareers] = useState(true)
  const [selectedCareerId, setSelectedCareerId] = useState("medicina-udec")
  const [selectedRegionFilter, setSelectedRegionFilter] = useState("ALL")
  const [selectedUniversityFilter, setSelectedUniversityFilter] = useState("ALL")
  const [scopeFilter, setScopeFilter] = useState("POPULAR") // "POPULAR" | "ALL"
  const [selectedCampusFilter, setSelectedCampusFilter] = useState("ALL")
  const [searchTerm, setSearchTerm] = useState("")

  // Factores académicos (NEM, Ranking) y pruebas PAES calibrados con tabla oficial DEMRE Grupo A
  const [nem, setNem] = useState(713)
  const [nemGrade, setNemGrade] = useState(6.00) // 6.00 = 713 pts oficiales DEMRE Grupo A
  const [ranking, setRanking] = useState(713) // Predeterminado igual al NEM
  const [m1, setM1] = useState(800)
  const [lectura, setLectura] = useState(780)
  const [m2, setM2] = useState(700)
  const [ciencias, setCiencias] = useState(720)
  const [historia, setHistoria] = useState(650)

  const handleNemChange = (newScore) => {
    const s = Math.max(100, Math.min(1000, Number(newScore)))
    setNem(s)
    setNemGrade(gradeFromNem(s))
    if (ranking < s) {
      setRanking(s)
    }
  }

  const handleGradeChange = (newGrade) => {
    const g = Number(newGrade)
    setNemGrade(g)
    const s = nemFromGrade(g)
    setNem(s)
    if (ranking < s) {
      setRanking(s)
    }
  }

  const handleRankingChange = (newRanking) => {
    const r = Math.max(nem, Math.min(1000, Number(newRanking)))
    setRanking(r)
  }

  // Estado de simulación
  const [simulation, setSimulation] = useState(null)
  const [simulating, setSimulating] = useState(false)
  const [error, setError] = useState(null)

  // Cargar catálogo de carreras al montar
  useEffect(() => {
    let isMounted = true
    async function fetchCareers() {
      try {
        setLoadingCareers(true)
        const res = await api.paes.admission.getCareers()
        if (isMounted && res.careers && res.careers.length > 0) {
          setCareers(res.careers)
          const defaultCareer = res.careers.find((c) => c.id === "medicina-udec") || res.careers[0]
          setSelectedCareerId(defaultCareer.id)
          if (res.careers.some((c) => c.region === "Biobío")) {
            setSelectedRegionFilter("Biobío")
          }
        }
      } catch (err) {
        console.error("Error cargando carreras CRUCH:", err)
        if (isMounted) setError("No se pudo cargar el catálogo de universidades.")
      } finally {
        if (isMounted) setLoadingCareers(false)
      }
    }
    fetchCareers()
    return () => {
      isMounted = false
    }
  }, [])

  // Ejecutar simulación cuando cambian los inputs
  const runSimulation = useCallback(async () => {
    if (!selectedCareerId) return
    try {
      setSimulating(true)
      setError(null)
      const payload = {
        career_id: selectedCareerId,
        nem: Number(nem),
        ranking: Number(ranking),
        scores: {
          m1: Number(m1),
          lectura: Number(lectura),
          m2: Number(m2),
          ciencias: Number(ciencias),
          historia: Number(historia),
        },
      }
      const res = await api.paes.admission.simulate(payload)
      if (res && res.simulation) {
        setSimulation(res.simulation)
      }
    } catch (err) {
      console.error("Error en simulación CRUCH:", err)
      setError(err.message || "Error al calcular la admisión.")
    } finally {
      setSimulating(false)
    }
  }, [selectedCareerId, nem, ranking, m1, lectura, m2, ciencias, historia])

  // Debounce para actualizar suavemente al mover sliders
  useEffect(() => {
    const timer = setTimeout(() => {
      runSimulation()
    }, 200)
    return () => clearTimeout(timer)
  }, [runSimulation])

  // Heurística de alta demanda / carreras populares
  const isPopularCareer = useCallback((c) => {
    if (c.is_popular === true) return true
    const cutoff2026 = Number(c.cutoffs?.["2026"] || c.cutoffs?.["2025"] || 0)
    if (cutoff2026 >= 720) return true
    const popularRegex =
      /(medicina|odontolog|enfermer|obstetricia|kinesiolog|psicolog|derecho|arquitectura|civil industrial|civil inform|civil plan com|civil el[eé]ctrica|civil qu[ií]mica|civil mec[aá]nica|automatiz|ingenier.*comercial|auditor|trabajo social|farmacia|bioqu|tecnolog.*m[eé]dica|veterinaria|educaci[oó]n diferencial)/i
    return popularRegex.test(c.name || "")
  }, [])

  // Regiones disponibles en los datos
  const availableRegions = useMemo(() => {
    const regSet = new Set()
    careers.forEach((c) => {
      if (c.region) regSet.add(c.region)
    })
    const regionPills = [{ id: "ALL", label: " Todas las Regiones"}]
    const regionIcons = {
      Biobío: "",
      Ñuble: "",
      Maule: "",
      Metropolitana: "",
      Valparaíso: "",
    }
    const regionNames = {
      Biobío: "Región del Biobío",
      Ñuble: "Región de Ñuble",
      Maule: "Región del Maule",
      Metropolitana: "Región Metropolitana",
      Valparaíso: "Región de Valparaíso",
    }
    const preferredOrder = ["Biobío", "Ñuble", "Maule", "Metropolitana", "Valparaíso"]
    preferredOrder.forEach((r) => {
      if (regSet.has(r)) {
        regionPills.push({
          id: r,
          label: `${regionIcons[r] || ""} ${regionNames[r] || `Región de ${r}`}`,
        })
        regSet.delete(r)
      }
    })
    regSet.forEach((r) => {
      regionPills.push({ id: r, label: ` ${r}` })
    })
    return regionPills
  }, [careers])

  // Universidades disponibles dinámicamente según la región seleccionada
  const availableUniversities = useMemo(() => {
    let pool = careers
    if (selectedRegionFilter !== "ALL") {
      pool = pool.filter((c) => c.region === selectedRegionFilter)
    }
    const map = new Map()
    pool.forEach((c) => {
      if (c.university_short && !map.has(c.university_short)) {
        map.set(c.university_short, c.university || c.university_short)
      }
    })

    const shortLabels = {
      UdeC: "U. de Concepción",
      UBB: "U. del Bío-Bío",
      UCSC: "UCSC",
      UTALCA: "U. de Talca",
      UCM: "U. Católica del Maule",
      UA: "U. Autónoma (Talca)",
      UCH: "U. de Chile",
      PUC: "Católica (PUC)",
      USACH: "USACH",
      UTFSM: "Santa María",
    }

    const items = [
      {
        id: "ALL",
        label: selectedRegionFilter === "ALL" ? "Todas las Universidades" : `Todas en ${selectedRegionFilter}`,
      },
    ]

    map.forEach((fullName, shortCode) => {
      items.push({
        id: shortCode,
        label: shortLabels[shortCode] || shortCode,
      })
    })

    return items
  }, [careers, selectedRegionFilter])

  // Filtrado de carreras por región, universidad, campus, alcance y búsqueda
  const filteredCareers = useMemo(() => {
    let list = careers

    if (selectedRegionFilter !== "ALL") {
      list = list.filter((c) => c.region === selectedRegionFilter)
    }

    if (selectedUniversityFilter !== "ALL") {
      list = list.filter((c) => c.university_short === selectedUniversityFilter)
    }

    if (selectedCampusFilter !== "ALL") {
      list = list.filter((c) => (c.campus || "").toLowerCase().includes(selectedCampusFilter.toLowerCase()))
    }

    if (scopeFilter === "POPULAR" && !searchTerm.trim()) {
      const popList = list.filter(isPopularCareer)
      if (popList.length > 0) {
        list = popList
      }
    }

    if (searchTerm.trim()) {
      const q = searchTerm.toLowerCase().trim()
      list = list.filter(
        (c) =>
          (c.name || "").toLowerCase().includes(q) ||
          (c.code || "").includes(q) ||
          (c.area || "").toLowerCase().includes(q) ||
          (c.campus || "").toLowerCase().includes(q)
      )
    }

    return list
  }, [
    careers,
    selectedRegionFilter,
    selectedUniversityFilter,
    selectedCampusFilter,
    scopeFilter,
    searchTerm,
    isPopularCareer,
  ])

  // Agrupación por Área de Estudio y ordenamiento por Puntaje de Corte 2026 descendente
  const AREA_PRIORITY = [
    "Ciencias de la Salud",
    "Ingeniería y Ciencias Exactas",
    "Ciencias Sociales y Jurídicas",
    "Ciencias Sociales",
    "Arquitectura, Arte y Diseño",
    "Educación",
    "Humanidades y Ciencias",
    "Ciencias Naturales y Agropecuarias",
  ]

  const groupedCareers = useMemo(() => {
    const map = {}
    filteredCareers.forEach((c) => {
      const area = c.area || "Otras Áreas"
      if (!map[area]) map[area] = []
      map[area].push(c)
    })

    Object.keys(map).forEach((area) => {
      map[area].sort((a, b) => {
        const scoreA = Number(a.cutoffs?.["2026"] || a.cutoffs?.["2025"] || 0)
        const scoreB = Number(b.cutoffs?.["2026"] || b.cutoffs?.["2025"] || 0)
        if (scoreB !== scoreA) return scoreB - scoreA
        return (a.name || "").localeCompare(b.name || "")
      })
    })

    const sortedEntries = []
    AREA_PRIORITY.forEach((area) => {
      if (map[area] && map[area].length > 0) {
        sortedEntries.push([area, map[area]])
        delete map[area]
      }
    })
    Object.entries(map).forEach(([area, list]) => {
      if (list.length > 0) sortedEntries.push([area, list])
    })

    return sortedEntries
  }, [filteredCareers])

  // Sincronizar carrera seleccionada si queda fuera de los filtros
  useEffect(() => {
    if (filteredCareers.length > 0) {
      const exists = filteredCareers.some((c) => c.id === selectedCareerId)
      if (!exists) {
        setSelectedCareerId(filteredCareers[0].id)
      }
    }
  }, [filteredCareers, selectedCareerId])

  const selectedCareer = useMemo(() => {
    return careers.find((c) => c.id === selectedCareerId) || filteredCareers[0] || careers[0]
  }, [careers, selectedCareerId, filteredCareers])

  // Cálculo en vivo instantáneo del puntaje ponderado oficial y aportes por prueba
  const liveWeighted = useMemo(() => {
    if (!selectedCareer || !selectedCareer.weights) {
      return { total: 0, gap: 0, electName: "Ciencias", electScore: 0, nemContrib: 0, rankContrib: 0, lecContrib: 0, m1Contrib: 0, m2Contrib: 0, electContrib: 0 }
    }
    const w = selectedCareer.weights
    const rule = w.elective_rule || "MAX"
    let electScore = 0
    let electName = "Ciencias"
    if (rule === "CIENCIAS") {
      electScore = Number(ciencias)
      electName = "Ciencias"
    } else if (rule === "HISTORIA") {
      electScore = Number(historia)
      electName = "Historia"
    } else {
      electScore = Math.max(Number(ciencias), Number(historia))
      electName = Number(ciencias) >= Number(historia) ? "Ciencias" : "Historia"
    }
    const electWeight = (w.ciencias || 0) + (w.historia || 0)
    const nemContrib = Number(nem) * (w.nem || 0)
    const rankContrib = Number(ranking) * (w.ranking || 0)
    const lecContrib = Number(lectura) * (w.lectura || 0)
    const m1Contrib = Number(m1) * (w.m1 || 0)
    const m2Contrib = Number(m2) * (w.m2 || 0)
    const electContrib = electScore * electWeight
    const total = nemContrib + rankContrib + lecContrib + m1Contrib + m2Contrib + electContrib
    const cutoff2026 = Number(selectedCareer.cutoffs?.["2026"] || 0)
    const gap = total - cutoff2026
    return {
      total,
      gap,
      electName,
      electScore,
      nemContrib,
      rankContrib,
      lecContrib,
      m1Contrib,
      m2Contrib,
      electContrib
    }
  }, [selectedCareer, nem, ranking, lectura, m1, m2, ciencias, historia])

  // Obtener estilo de la categoría de probabilidad
  const getProbabilityTheme = (category, prob) => {
    if (category === "Segura" || prob >= 85) {
      return {
        bg: "bg-emerald-500",
        border: "border-emerald-500/40",
        text: "text-emerald-400",
        bgLight: "bg-emerald-500/10",
        badge: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
        glow: "shadow-emerald-500/20",
        label: "Admisión Segura (>85%)",
        icon: "",
      }
    }
    if (category === "Competitiva" || prob >= 50) {
      return {
        bg: "bg-amber-500",
        border: "border-amber-500/40",
        text: "text-amber-400",
        bgLight: "bg-amber-500/10",
        badge: "bg-amber-500/20 text-amber-300 border-amber-500/30",
        glow: "shadow-amber-500/20",
        label: "Zona Competitiva (50% - 85%)",
        icon: "",
      }
    }
    return {
      bg: "bg-rose-500",
      border: "border-rose-500/40",
      text: "text-rose-400",
      bgLight: "bg-rose-500/10",
      badge: "bg-rose-500/20 text-rose-300 border-rose-500/30",
      glow: "shadow-rose-500/20",
      label: "Zona Riesgosa (<50%)",
      icon: "",
    }
  }

  const probTheme = getProbabilityTheme(
    simulation?.category || "Competitiva",
    simulation?.probability || 50
  )

  return (
    <div className="space-y-8 animate-fade-in pb-12">
      {/* Encabezado Principal */}
      <div className="p-6 md:p-8 rounded-3xl bg-neutral-900/70 border border-white/[0.08] backdrop-blur-xl shadow-2xl relative overflow-hidden">
        <div className="absolute -right-16 -top-16 w-64 h-64 bg-sky-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 relative z-10">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="text-2xl"></span>
              <span className="text-xs font-mono font-bold tracking-wider uppercase text-sky-400">
                Admisión Universitaria Oficial DEMRE 2026
              </span>
            </div>
            <h2 className="text-2xl md:text-3xl font-black text-white tracking-tight">
              Simulador de Admisión & Probabilidad CRUCH
            </h2>
            <p className="text-xs md:text-sm text-neutral-400 max-w-2xl leading-relaxed">
              Calcula tu puntaje ponderado con las fórmulas oficiales de universidades top chilenas,
              proyecta la probabilidad psicométrica (IRT 3PL + Monte Carlo) y descubre la brecha
              exacta de aciertos necesarios para asegurar tu cupo.
            </p>
          </div>

          {simulation && (
            <div className={`p-4 rounded-2xl ${probTheme.bgLight} border ${probTheme.border} text-center min-w-[180px] shadow-lg ${probTheme.glow}`}>
              <div className="text-[11px] font-mono uppercase tracking-wider text-neutral-400">
                Puntaje Ponderado
              </div>
              <div className={`text-3xl font-black ${probTheme.text} font-mono my-1`}>
                {simulation.weighted_score.toFixed(2)}
              </div>
              <div className="text-[11px] text-neutral-400">
                Corte 2026: <strong className="text-white">{simulation.target_cutoff.toFixed(2)}</strong>
              </div>
            </div>
          )}
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-2xl bg-rose-500/15 border border-rose-500/30 text-rose-300 text-xs flex items-center justify-between">
          <span>{error}</span>
          <button onClick={runSimulation} className="underline font-bold cursor-pointer">
            Reintentar
          </button>
        </div>
      )}

      {/* Grid de Configuración: Carrera Objetiva + Sliders de Puntaje */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Columna Izquierda: Selección de Carrera y Universidad (4 cols) */}
        <div className="lg:col-span-5 space-y-6">
          <div className="p-6 rounded-3xl bg-neutral-900/60 border border-white/[0.08] backdrop-blur-xl shadow-xl space-y-5">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-black uppercase tracking-wider text-white flex items-center gap-2">
                Carrera & Universidad Objetivo
              </h3>
              {selectedCareer?.requires_m2 && (
                <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-md bg-amber-500/20 text-amber-300 border border-amber-500/30">
                  Exige M2
                </span>
              )}
            </div>

            {/* 1. Filtro de Región */}
            {availableRegions.length > 1 && (
              <div className="space-y-1.5">
                <div className="flex justify-between items-center text-[11px] font-mono">
                  <span className="text-neutral-400 font-semibold uppercase tracking-wider">1. Región Geográfica:</span>
                  <span className="text-neutral-500">{selectedRegionFilter === "ALL" ? "Nacional" : selectedRegionFilter}</span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {availableRegions.map((r) => (
                    <button
                      key={r.id}
                      type="button"
                      onClick={() => {
                        setSelectedRegionFilter(r.id)
                        setSelectedUniversityFilter("ALL")
                        setSelectedCampusFilter("ALL")
                      }}
                      className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold transition-all cursor-pointer ${
                        selectedRegionFilter === r.id
                          ? "bg-sky-500 text-neutral-950 font-bold shadow-sm"
                          : "bg-white/[0.04] text-neutral-400 hover:text-white hover:bg-white/[0.08]"
                      }`}
                    >
                      {r.label}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* 2. Filtro de Universidad */}
            <div className="space-y-1.5">
              <div className="flex justify-between items-center text-[11px] font-mono">
                <span className="text-neutral-400 font-semibold uppercase tracking-wider">2. Universidad:</span>
                <span className="text-neutral-500">{selectedUniversityFilter === "ALL" ? "Todas" : selectedUniversityFilter}</span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {availableUniversities.map((u) => (
                  <button
                    key={u.id}
                    type="button"
                    onClick={() => {
                      setSelectedUniversityFilter(u.id)
                      setSelectedCampusFilter("ALL")
                    }}
                    className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold transition-all cursor-pointer ${
                      selectedUniversityFilter === u.id
                        ? "bg-sky-500 text-neutral-950 font-bold shadow-sm"
                        : "bg-white/[0.04] text-neutral-400 hover:text-white hover:bg-white/[0.08]"
                    }`}
                  >
                    {u.label}
                  </button>
                ))}
              </div>
            </div>

            {/* 3. Filtro de Alcance: Populares vs Catálogo Completo */}
            <div className="flex items-center justify-between p-1 rounded-xl bg-neutral-950/70 border border-white/[0.06]">
              <span className="text-[10px] font-mono text-neutral-400 px-2 uppercase tracking-wider font-semibold">
                Alcance:
              </span>
              <div className="flex gap-1">
                <button
                  type="button"
                  onClick={() => setScopeFilter("POPULAR")}
                  className={`px-3 py-1 rounded-lg text-[11px] font-semibold transition-all cursor-pointer ${
                    scopeFilter === "POPULAR"
                      ? "bg-amber-500/20 text-amber-300 border border-amber-500/40 font-bold shadow-sm"
                      : "text-neutral-400 hover:text-white"
                  }`}
                  title="Filtra por carreras de alta demanda y mayor interés general"
                >
                   Top / Alta Demanda
                </button>
                <button
                  type="button"
                  onClick={() => setScopeFilter("ALL")}
                  className={`px-3 py-1 rounded-lg text-[11px] font-semibold transition-all cursor-pointer ${
                    scopeFilter === "ALL"
                      ? "bg-sky-500/20 text-sky-300 border border-sky-500/40 font-bold shadow-sm"
                      : "text-neutral-400 hover:text-white"
                  }`}
                  title="Muestra todas las carreras disponibles sin excepción"
                >
                   Catálogo Completo
                </button>
              </div>
            </div>

            {/* Buscador de Carreras y Filtro de Campus */}
            <div className="space-y-3">
              <div className="relative">
                <input
                  type="text"
                  placeholder=" Buscar carrera (ej. Aeroespacial, Medicina, Derecho, 13086)..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full bg-neutral-950/70 border border-white/[0.1] rounded-xl px-3.5 py-2 text-white text-xs placeholder:text-neutral-500 focus:outline-none focus:border-sky-500"
                />
                {searchTerm && (
                  <button
                    type="button"
                    onClick={() => setSearchTerm("")}
                    className="absolute right-2.5 top-2 text-xs text-neutral-400 hover:text-white"
                  >
                    
                  </button>
                )}
              </div>

              {/* Campus Pills si existen sedes específicas */}
              {["Concepción", "Chillán", "Los Ángeles", "Talca", "Curicó"].some((cp) =>
                filteredCareers.some((c) => (c.campus || "").toLowerCase().includes(cp.toLowerCase()))
              ) && (
                <div className="flex items-center gap-1.5 overflow-x-auto text-[10px] font-mono">
                  <span className="text-neutral-500">Campus:</span>
                  {[
                    { id: "ALL", label: "Todos" },
                    { id: "Concepción", label: "Concepción" },
                    { id: "Chillán", label: "Chillán" },
                    { id: "Los Ángeles", label: "Los Ángeles" },
                    { id: "Talca", label: "Talca" },
                    { id: "Curicó", label: "Curicó" },
                  ]
                    .filter(
                      (cp) =>
                        cp.id === "ALL" ||
                        filteredCareers.some((c) =>
                          (c.campus || "").toLowerCase().includes(cp.id.toLowerCase())
                        )
                    )
                    .map((cp) => (
                      <button
                        key={cp.id}
                        type="button"
                        onClick={() => setSelectedCampusFilter(cp.id)}
                        className={`px-2 py-0.5 rounded transition-colors cursor-pointer ${
                          selectedCampusFilter === cp.id
                            ? "bg-sky-500/20 text-sky-300 font-bold border border-sky-500/30"
                            : "bg-white/[0.03] text-neutral-400 hover:text-white"
                        }`}
                      >
                        {cp.label}
                      </button>
                    ))}
                </div>
              )}

              {/* Selector de Carrera Agrupado por Área y Ordenado por Corte */}
              <div className="space-y-1.5">
                <div className="flex justify-between items-center text-xs">
                  <label className="text-neutral-400 font-medium">Seleccionar Carrera:</label>
                  <span className="text-[10px] font-mono text-sky-400 font-bold">
                    {filteredCareers.length} disponibles
                  </span>
                </div>
                <select
                  value={selectedCareerId}
                  onChange={(e) => setSelectedCareerId(e.target.value)}
                  disabled={loadingCareers}
                  className="w-full bg-neutral-800/90 border border-white/[0.1] rounded-2xl px-4 py-3 text-white text-xs md:text-sm font-semibold focus:outline-none focus:border-sky-500 transition-colors cursor-pointer"
                >
                  {groupedCareers.length === 0 ? (
                    <option value="" disabled className="bg-neutral-900 text-neutral-400">
                      No hay carreras disponibles con estos filtros
                    </option>
                  ) : (
                    groupedCareers.map(([area, careerList]) => (
                      <optgroup
                        key={area}
                        label={`── ${area.toUpperCase()} (${careerList.length}) ──`}
                        className="bg-neutral-950 text-sky-400 font-bold py-1"
                      >
                        {careerList.map((c) => (
                          <option key={c.id} value={c.id} className="bg-neutral-900 text-white font-normal py-1">
                            {c.name} ({c.campus}) — {c.university_short} • Corte '26: {c.cutoffs?.["2026"] || "---"} pts
                          </option>
                        ))}
                      </optgroup>
                    ))
                  )}
                </select>
              </div>
            </div>

            {/* Ficha Rápida de la Carrera Seleccionada */}
            {selectedCareer && (
              <div className="p-4 rounded-2xl bg-neutral-800/40 border border-white/[0.06] space-y-3 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-white text-sm">{selectedCareer.name}</span>
                  <span className="px-2 py-0.5 rounded bg-sky-500/10 text-sky-400 font-mono text-[10px] font-bold">
                    {selectedCareer.university_short}
                  </span>
                </div>
                <div className="flex items-center justify-between flex-wrap gap-2 text-neutral-400 text-[11px]">
                  <span>
                     {selectedCareer.university} • {selectedCareer.campus}
                  </span>
                  <a
                    href={getCareerUrl(selectedCareer)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-sky-400 hover:text-sky-300 hover:underline font-medium text-[11px] shrink-0 transition-colors"
                  >
                    <span>Link de la carrera</span>
                    <span aria-hidden="true" className="text-[10px]">↗</span>
                  </a>
                </div>

                {/* Histórico de Cortes */}
                <div className="pt-2 border-t border-white/[0.06] grid grid-cols-3 gap-2 text-center">
                  <div className="p-2 rounded-xl bg-black/20">
                    <div className="text-[10px] text-neutral-500 font-mono">Corte 2024</div>
                    <div className="font-mono font-bold text-neutral-300">{selectedCareer.cutoffs["2024"]}</div>
                  </div>
                  <div className="p-2 rounded-xl bg-black/20">
                    <div className="text-[10px] text-neutral-500 font-mono">Corte 2025</div>
                    <div className="font-mono font-bold text-neutral-300">{selectedCareer.cutoffs["2025"]}</div>
                  </div>
                  <div className="p-2 rounded-xl bg-sky-500/10 border border-sky-500/20">
                    <div className="text-[10px] text-sky-400 font-mono font-bold">Corte 2026</div>
                    <div className="font-mono font-black text-sky-300">{selectedCareer.cutoffs["2026"]}</div>
                  </div>
                </div>

                {/* Ponderaciones Oficiales */}
                <div className="pt-2 text-[11px] text-neutral-400 space-y-1.5">
                  <div className="font-bold text-neutral-300 text-[10px] uppercase font-mono">
                    Ponderaciones Oficiales:
                  </div>
                  <div className="flex flex-wrap gap-1.5 font-mono text-[10px]">
                    <span className="px-2 py-0.5 rounded bg-white/[0.05]">NEM: {Math.round(selectedCareer.weights.nem * 100)}%</span>
                    <span className="px-2 py-0.5 rounded bg-white/[0.05]">Rank: {Math.round(selectedCareer.weights.ranking * 100)}%</span>
                    <span className="px-2 py-0.5 rounded bg-white/[0.05]">Lec: {Math.round(selectedCareer.weights.lectura * 100)}%</span>
                    <span className="px-2 py-0.5 rounded bg-white/[0.05]">M1: {Math.round(selectedCareer.weights.m1 * 100)}%</span>
                    {selectedCareer.weights.m2 > 0 && (
                      <span className="px-2 py-0.5 rounded bg-amber-500/15 text-amber-300">M2: {Math.round(selectedCareer.weights.m2 * 100)}%</span>
                    )}
                    <span className="px-2 py-0.5 rounded bg-white/[0.05]">
                      {selectedCareer.weights.elective_rule === "CIENCIAS" ? "Ciencias: " : selectedCareer.weights.elective_rule === "HISTORIA" ? "Historia: " : "Electiva (Max): "}
                      {Math.round((selectedCareer.weights.ciencias + selectedCareer.weights.historia) * 100)}%
                    </span>
                  </div>
                </div>

                {/* Puntaje Ponderado en Vivo */}
                <div className="pt-2.5 border-t border-white/[0.08] flex items-center justify-between text-xs">
                  <div>
                    <span className="text-[10px] text-neutral-400 font-mono uppercase block">Tu Ponderado Actual</span>
                    <span className="font-mono font-black text-sky-400 text-sm">
                      {liveWeighted.total.toFixed(2)} pts
                    </span>
                  </div>
                  <div className="text-right font-mono text-[10px]">
                    <span className={liveWeighted.gap >= 0 ? "text-emerald-400 font-bold" : "text-amber-400 font-bold"}>
                      {liveWeighted.gap >= 0 ? `+${liveWeighted.gap.toFixed(2)} pts (Sobre Corte)` : `${liveWeighted.gap.toFixed(2)} pts (Bajo Corte)`}
                    </span>
                    <div className="text-neutral-500">Corte '26: {selectedCareer.cutoffs["2026"]}</div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Columna Derecha: Controles de Puntajes (NEM, Ranking, Pruebas) (7 cols) */}
        <div className="lg:col-span-7 space-y-6">
          <div className="p-6 rounded-3xl bg-neutral-900/60 border border-white/[0.08] backdrop-blur-xl shadow-xl space-y-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-black uppercase tracking-wider text-white flex items-center gap-2">
                  Tus Puntajes Estimados o Simulados
                </h3>
                <span className="text-[11px] font-mono text-neutral-500 font-normal">Escala DEMRE 100 - 1000</span>
              </div>
              <div className="px-3 py-1.5 rounded-xl bg-sky-500/10 border border-sky-500/30 font-mono text-right">
                <span className="text-[10px] text-neutral-400 uppercase block">Tu Ponderado</span>
                <span className="text-sm font-black text-sky-300">
                  {liveWeighted.total.toFixed(2)} pts
                </span>
              </div>
            </div>

            {/* Factores Escolares: NEM y Ranking */}
            <div className="p-4 rounded-2xl bg-neutral-950/60 border border-white/[0.08] space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-white/[0.06]">
                <div className="space-y-0.5">
                  <div className="text-xs font-bold text-white flex items-center gap-1.5">
                    Trayectoria Escolar (DEMRE Grupo A)
                  </div>
                  <p className="text-[10px] text-neutral-400">
                    Conversión oficial de notas y bonificación de contexto educativo.
                  </p>
                </div>
                {selectedCareer && (
                  <span className="px-2.5 py-1 rounded-full bg-sky-500/10 border border-sky-500/20 text-sky-300 font-mono text-[10px] font-bold">
                    Ponderación en esta carrera: {Math.round(((selectedCareer.weights.nem || 0) + (selectedCareer.weights.ranking || 0)) * 100)}%
                  </span>
                )}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Panel NEM */}
                <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06] space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="text-xs font-bold text-neutral-200">NEM (Notas Enseñanza Media)</span>
                      <div className="text-[10px] text-neutral-400 font-mono">Tabla Oficial DEMRE Grupo A (301 notas)</div>
                    </div>
                    <div className="text-right">
                      <span className="font-mono font-black text-sky-400 text-sm">{nem} pts</span>
                      <div className="text-[10px] font-bold text-emerald-400 font-mono">Nota {nemGrade.toFixed(2)}</div>
                    </div>
                  </div>

                  {/* Dual Input Controls: Nota y Puntaje */}
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <label className="text-[10px] text-neutral-400 font-mono block mb-1">Promedio Notas (4.0 - 7.0)</label>
                      <input
                        type="number"
                        min="4.00"
                        max="7.00"
                        step="0.01"
                        value={nemGrade}
                        onChange={(e) => handleGradeChange(e.target.value)}
                        className="w-full px-2.5 py-1.5 rounded-lg bg-neutral-900 border border-white/10 text-white font-mono text-xs focus:outline-none focus:border-sky-500"
                      />
                    </div>
                    <div>
                      <label className="text-[10px] text-neutral-400 font-mono block mb-1">Puntaje NEM (100 - 1000)</label>
                      <input
                        type="number"
                        min="100"
                        max="1000"
                        step="1"
                        value={nem}
                        onChange={(e) => handleNemChange(e.target.value)}
                        className="w-full px-2.5 py-1.5 rounded-lg bg-neutral-900 border border-white/10 text-sky-400 font-mono text-xs focus:outline-none focus:border-sky-500"
                      />
                    </div>
                  </div>

                  <input
                    type="range"
                    min="100"
                    max="1000"
                    step="5"
                    value={nem}
                    onChange={(e) => handleNemChange(e.target.value)}
                    className="w-full accent-sky-500 cursor-pointer h-1.5 bg-neutral-800 rounded-lg appearance-none"
                  />
                  <div className="flex justify-between text-[10px] text-neutral-500 font-mono">
                    <span>4.00 (100 pts)</span>
                    <span>5.50 (572 pts)</span>
                    <span>7.00 (1000 pts)</span>
                  </div>
                </div>

                {/* Panel Ranking */}
                <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06] space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="text-xs font-bold text-neutral-200">Ranking de Notas</span>
                      <div className="text-[10px] text-neutral-400 font-mono">
                        {ranking > nem ? `Bonificación: +${ranking - nem} pts sobre NEM` : "Igual a NEM (base sin bonificación)"}
                      </div>
                    </div>
                    <div className="text-right">
                      <span className="font-mono font-black text-sky-400 text-sm">{ranking} pts</span>
                      <div className="text-[10px] font-bold text-sky-400 font-mono">
                        {ranking === 1000 ? "Máx. Histórico / Top 10%" : ranking > nem ? "Sobre la media escolar" : "Media escolar"}
                      </div>
                    </div>
                  </div>

                  {/* Presets Rápidos de Ranking */}
                  <div className="flex items-center gap-1.5 pt-0.5">
                    <span className="text-[10px] text-neutral-500 font-mono">Presets:</span>
                    <button
                      type="button"
                      onClick={() => handleRankingChange(nem)}
                      className={`px-2 py-0.5 rounded text-[10px] font-mono transition-colors ${
                        ranking === nem ? "bg-sky-500 text-white font-bold" : "bg-neutral-800 text-neutral-400 hover:text-white"
                      }`}
                    >
                      = NEM
                    </button>
                    <button
                      type="button"
                      onClick={() => handleRankingChange(nem + 30)}
                      className={`px-2 py-0.5 rounded text-[10px] font-mono transition-colors ${
                        ranking === nem + 30 ? "bg-sky-500 text-white font-bold" : "bg-neutral-800 text-neutral-400 hover:text-white"
                      }`}
                    >
                      +30
                    </button>
                    <button
                      type="button"
                      onClick={() => handleRankingChange(nem + 80)}
                      className={`px-2 py-0.5 rounded text-[10px] font-mono transition-colors ${
                        ranking === nem + 80 ? "bg-sky-500 text-white font-bold" : "bg-neutral-800 text-neutral-400 hover:text-white"
                      }`}
                    >
                      +80
                    </button>
                    <button
                      type="button"
                      onClick={() => handleRankingChange(1000)}
                      className={`px-2 py-0.5 rounded text-[10px] font-mono transition-colors ${
                        ranking === 1000 ? "bg-sky-500 text-white font-bold" : "bg-neutral-800 text-neutral-400 hover:text-white"
                      }`}
                    >
                      1000
                    </button>
                  </div>

                  <input
                    type="range"
                    min={nem}
                    max="1000"
                    step="5"
                    value={ranking}
                    onChange={(e) => handleRankingChange(e.target.value)}
                    className="w-full accent-sky-500 cursor-pointer h-1.5 bg-neutral-800 rounded-lg appearance-none"
                  />
                  <div className="flex justify-between text-[10px] text-neutral-500 font-mono">
                    <span>Base NEM ({nem})</span>
                    <span>Ranking ≥ NEM (Norma DEMRE)</span>
                    <span>1000</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Pruebas Obligatorias y Electivas */}
            <div className="space-y-4">
              {/* M1 */}
              <div className="space-y-1.5">
                <div className="flex justify-between items-center text-xs">
                  <span className="font-bold text-white flex items-center gap-1.5">
                    Competencia Matemática 1 (M1)
                    {selectedCareer && (
                      <span className="text-[10px] font-mono text-sky-400 font-semibold">
                        ({Math.round((selectedCareer.weights?.m1 || 0) * 100)}% • Aporta {liveWeighted.m1Contrib.toFixed(1)} pts)
                      </span>
                    )}
                  </span>
                  <span className="font-mono font-black text-white text-sm">{m1} pts</span>
                </div>
                <input
                  type="range"
                  min="100"
                  max="1000"
                  step="5"
                  value={m1}
                  onChange={(e) => setM1(Number(e.target.value))}
                  className="w-full accent-sky-400 cursor-pointer h-1.5 bg-neutral-800 rounded-lg appearance-none"
                />
              </div>

              {/* Comp Lectora */}
              <div className="space-y-1.5">
                <div className="flex justify-between items-center text-xs">
                  <span className="font-bold text-white flex items-center gap-1.5">
                    Competencia Lectora
                    {selectedCareer && (
                      <span className="text-[10px] font-mono text-sky-400 font-semibold">
                        ({Math.round((selectedCareer.weights?.lectura || 0) * 100)}% • Aporta {liveWeighted.lecContrib.toFixed(1)} pts)
                      </span>
                    )}
                  </span>
                  <span className="font-mono font-black text-white text-sm">{lectura} pts</span>
                </div>
                <input
                  type="range"
                  min="100"
                  max="1000"
                  step="5"
                  value={lectura}
                  onChange={(e) => setLectura(Number(e.target.value))}
                  className="w-full accent-sky-400 cursor-pointer h-1.5 bg-neutral-800 rounded-lg appearance-none"
                />
              </div>

              {/* M2 */}
              <div className="space-y-1.5">
                <div className="flex justify-between items-center text-xs">
                  <span className="font-bold text-white flex items-center gap-1.5">
                    Competencia Matemática 2 (M2)
                    {selectedCareer && (
                      (selectedCareer.weights?.m2 || 0) > 0 ? (
                        <span className="text-[10px] font-mono text-amber-300 font-semibold">
                          ({Math.round(selectedCareer.weights.m2 * 100)}% Exigida • Aporta {liveWeighted.m2Contrib.toFixed(1)} pts)
                        </span>
                      ) : (
                        <span className="text-[10px] font-mono text-neutral-500 font-normal">
                          (No pondera: 0% en esta carrera)
                        </span>
                      )
                    )}
                  </span>
                  <span className="font-mono font-black text-white text-sm">{m2} pts</span>
                </div>
                <input
                  type="range"
                  min="100"
                  max="1000"
                  step="5"
                  value={m2}
                  onChange={(e) => setM2(Number(e.target.value))}
                  className="w-full accent-amber-400 cursor-pointer h-1.5 bg-neutral-800 rounded-lg appearance-none"
                />
              </div>

              {/* Electivas: Ciencias e Historia */}
              <div className="space-y-2 pt-1 border-t border-white/[0.06]">
                <div className="flex items-center justify-between text-xs pt-1">
                  <span className="font-bold text-white text-xs flex items-center gap-1.5">
                    <span> / </span> Pruebas Electivas
                  </span>
                  {selectedCareer && (
                    <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-purple-500/10 text-purple-300 border border-purple-500/20">
                      {selectedCareer.weights?.elective_rule === "CIENCIAS"
                        ? `Exige solo Ciencias (${Math.round((selectedCareer.weights?.ciencias || 0) * 100)}%)`
                        : selectedCareer.weights?.elective_rule === "HISTORIA"
                        ? `Exige solo Historia (${Math.round((selectedCareer.weights?.historia || 0) * 100)}%)`
                        : `Regla DEMRE: Mejor Puntaje (${Math.round(((selectedCareer.weights?.ciencias || 0) + (selectedCareer.weights?.historia || 0)) * 100)}%)`}
                    </span>
                  )}
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-1.5 p-2.5 rounded-xl bg-white/[0.015] border border-white/[0.04]">
                    <div className="flex justify-between items-center text-xs">
                      <div>
                        <span className="font-bold text-neutral-300 block">Ciencias</span>
                        {selectedCareer && (
                          liveWeighted.electName === "Ciencias" && (selectedCareer.weights?.ciencias > 0 || selectedCareer.weights?.elective_rule === "MAX") ? (
                            <span className="text-[9px] font-mono text-emerald-400 font-bold">● Activa en ponderado (+{liveWeighted.electContrib.toFixed(1)} pts)</span>
                          ) : selectedCareer.weights?.ciencias === 0 && selectedCareer.weights?.elective_rule === "HISTORIA" ? (
                            <span className="text-[9px] font-mono text-neutral-500">○ No pondera (0%)</span>
                          ) : (
                            <span className="text-[9px] font-mono text-neutral-500">○ Descartada por menor puntaje</span>
                          )
                        )}
                      </div>
                      <span className="font-mono font-bold text-neutral-300">{ciencias} pts</span>
                    </div>
                    <input
                      type="range"
                      min="100"
                      max="1000"
                      step="5"
                      value={ciencias}
                      onChange={(e) => setCiencias(Number(e.target.value))}
                      className="w-full accent-purple-400 cursor-pointer h-1.5 bg-neutral-800 rounded-lg appearance-none"
                    />
                  </div>

                  <div className="space-y-1.5 p-2.5 rounded-xl bg-white/[0.015] border border-white/[0.04]">
                    <div className="flex justify-between items-center text-xs">
                      <div>
                        <span className="font-bold text-neutral-300 block">Historia y Cs. Sociales</span>
                        {selectedCareer && (
                          liveWeighted.electName === "Historia" && (selectedCareer.weights?.historia > 0 || selectedCareer.weights?.elective_rule === "MAX") ? (
                            <span className="text-[9px] font-mono text-emerald-400 font-bold">● Activa en ponderado (+{liveWeighted.electContrib.toFixed(1)} pts)</span>
                          ) : selectedCareer.weights?.historia === 0 && selectedCareer.weights?.elective_rule === "CIENCIAS" ? (
                            <span className="text-[9px] font-mono text-neutral-500">○ No pondera (0%)</span>
                          ) : (
                            <span className="text-[9px] font-mono text-neutral-500">○ Descartada por menor puntaje</span>
                          )
                        )}
                      </div>
                      <span className="font-mono font-bold text-neutral-300">{historia} pts</span>
                    </div>
                    <input
                      type="range"
                      min="100"
                      max="1000"
                      step="5"
                      value={historia}
                      onChange={(e) => setHistoria(Number(e.target.value))}
                      className="w-full accent-purple-400 cursor-pointer h-1.5 bg-neutral-800 rounded-lg appearance-none"
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* SECCIÓN DE RESULTADOS & DIAGNÓSTICO PSICOMÉTRICO */}
      {simulation && (
        <div className="space-y-6">
          {/* Barra Viva de Probabilidad Psicométrica Monte Carlo */}
          <div className="p-6 md:p-8 rounded-3xl bg-neutral-900/70 border border-white/[0.08] backdrop-blur-xl shadow-2xl space-y-6">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xl">{probTheme.icon}</span>
                  <h3 className="text-lg font-black text-white">
                    Probabilidad de Admisión Proyectada
                  </h3>
                  <span className={`px-2.5 py-0.5 rounded-full text-xs font-mono font-bold border ${probTheme.badge}`}>
                    {simulation.category}
                  </span>
                </div>
                <p className="text-xs text-neutral-400 max-w-xl">
                  {simulation.status_message}
                </p>
              </div>

              <div className="text-left md:text-right">
                <div className="text-4xl md:text-5xl font-black font-mono text-white tracking-tight">
                  {simulation.probability.toFixed(1)}%
                </div>
                <div className="text-[11px] font-mono text-neutral-400">
                  Intervalo Confianza 95%: [{simulation.confidence_interval_95[0]} - {simulation.confidence_interval_95[1]}] pts
                </div>
              </div>
            </div>

            {/* Barra de Progreso Dinámica */}
            <div className="space-y-2">
              <div className="h-4 w-full bg-neutral-800/90 rounded-full overflow-hidden p-0.5 border border-white/[0.06]">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${probTheme.bg} shadow-md`}
                  style={{ width: `${Math.max(5, Math.min(100, simulation.probability))}%` }}
                />
              </div>
              <div className="flex justify-between text-[11px] font-mono text-neutral-400">
                <span>0% (Riesgosa)</span>
                <span className="text-amber-400/80">50% (Competitiva)</span>
                <span className="text-emerald-400/80">85% (Segura)</span>
                <span>100%</span>
              </div>
            </div>
          </div>

          {/* Tarjeta de "Brecha a la Meta" y Aciertos Requeridos */}
          <div className="p-6 md:p-8 rounded-3xl bg-neutral-900/70 border border-white/[0.08] backdrop-blur-xl shadow-2xl space-y-6">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-white/[0.06]">
              <div>
                <h3 className="text-lg font-black text-white flex items-center gap-2">
                  Brecha a la Meta de Admisión
                </h3>
                <p className="text-xs text-neutral-400">
                  {simulation.weighted_gap <= 0
                    ? "¡Estás por sobre el corte histórico de convocatoria! Tienes una holgura positiva."
                    : `Necesitas superar un déficit de ${simulation.weighted_gap.toFixed(2)} puntos ponderados para alcanzar el corte.`}
                </p>
              </div>

              <div className={`px-4 py-2 rounded-2xl font-mono font-bold text-sm ${
                simulation.weighted_gap <= 0 ? "bg-emerald-500/15 text-emerald-300 border border-emerald-500/30" : "bg-rose-500/15 text-rose-300 border border-rose-500/30"
              }`}>
                {simulation.weighted_gap <= 0
                  ? `+${Math.abs(simulation.weighted_gap).toFixed(2)} pts de Holgura`
                  : `-${simulation.weighted_gap.toFixed(2)} pts de Déficit`}
              </div>
            </div>

            {/* Grid de Pruebas: Aciertos y Puntos Necesarios por Prueba */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {Object.entries(simulation.gap_breakdown || {}).map(([key, item]) => {
                const isMet = simulation.weighted_gap <= 0 || item.additional_correct_needed === 0
                return (
                  <div
                    key={key}
                    className={`p-5 rounded-2xl border transition-all ${
                      isMet
                        ? "bg-emerald-500/[0.04] border-emerald-500/20"
                        : "bg-neutral-800/40 border-white/[0.06] hover:border-white/[0.15]"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-mono text-xs font-bold text-sky-400">
                        {item.subject_code} ({item.weight_percent}%)
                      </span>
                      {isMet ? (
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-bold">
                          Cumplido 
                        </span>
                      ) : (
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 font-bold">
                          +{item.net_points_needed} pts
                        </span>
                      )}
                    </div>

                    <div className="font-bold text-sm text-white mb-2">{item.subject_name}</div>

                    <div className="space-y-1.5 text-xs text-neutral-400 font-mono pt-2 border-t border-white/[0.04]">
                      <div className="flex justify-between">
                        <span>Puntaje actual:</span>
                        <strong className="text-white">{item.current_score} pts</strong>
                      </div>
                      <div className="flex justify-between">
                        <span>Aciertos estimados:</span>
                        <span className="text-neutral-300">{item.current_raw_items} correctas</span>
                      </div>

                      {!isMet && (
                        <>
                          <div className="flex justify-between pt-1 text-sky-300 font-bold">
                            <span>Objetivo si mejoras sola:</span>
                            <span>{item.target_score} pts</span>
                          </div>
                          <div className="flex justify-between text-amber-300 font-bold">
                            <span>Aciertos adicionales:</span>
                            <span>+{item.additional_correct_needed} preguntas</span>
                          </div>
                          {!item.is_achievable_alone && (
                            <div className="text-[10px] text-rose-400 pt-1 leading-tight">
                               Excede 1000 pts si intentas compensar todo solo con esta prueba. Conviene distribuir esfuerzos.
                            </div>
                          )}
                        </>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>

            {/* Plan de Mejora Equilibrado */}
            {simulation.balanced_plan && simulation.balanced_plan.length > 0 && simulation.weighted_gap > 0 && (
              <div className="p-5 rounded-2xl bg-sky-500/10 border border-sky-500/20 space-y-3">
                <div className="flex items-center gap-2">
                  <span className="text-lg"></span>
                  <h4 className="text-xs font-black uppercase font-mono tracking-wider text-sky-300">
                    Estrategia Recomendada: Distribución Equilibrada de Aciertos
                  </h4>
                </div>
                <p className="text-xs text-neutral-300 leading-relaxed">
                  En lugar de arriesgarte a obtener puntaje nacional en una sola prueba, puedes alcanzar el corte de{" "}
                  <strong>{simulation.career_name}</strong> repartiendo los aciertos según la ponderación de cada examen:
                </p>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 font-mono text-xs">
                  {simulation.balanced_plan.map((b) => (
                    <div key={b.subject_code} className="p-2.5 rounded-xl bg-black/30 border border-white/[0.06] text-center">
                      <div className="text-[10px] text-neutral-400">{b.subject_code}</div>
                      <div className="font-bold text-sky-400 my-0.5">+{b.net_points_gain} pts</div>
                      <div className="text-[10px] text-amber-300">+{b.additional_correct_needed} aciertos</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Comparador de Opciones en otras Carreras del Catálogo */}
          {simulation.all_careers_summary && simulation.all_careers_summary.length > 0 && (
            <div className="p-6 md:p-8 rounded-3xl bg-neutral-900/70 border border-white/[0.08] backdrop-blur-xl shadow-2xl space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-base font-black text-white flex items-center gap-2">
                    Pronóstico en otras Carreras CRUCH
                  </h3>
                  <p className="text-xs text-neutral-400">
                    Tu probabilidad proyectada con tus puntajes actuales en las principales carreras del país:
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {simulation.all_careers_summary.slice(0, 9).map((other) => {
                  const oTheme = getProbabilityTheme(other.category, other.probability)
                  const isCurrent = other.career_id === selectedCareerId
                  return (
                    <button
                      key={other.career_id}
                      onClick={() => setSelectedCareerId(other.career_id)}
                      className={`p-3.5 rounded-2xl border text-left transition-all cursor-pointer flex flex-col justify-between ${
                        isCurrent
                          ? "bg-sky-500/10 border-sky-500/40 ring-1 ring-sky-500/30"
                          : "bg-neutral-800/30 border-white/[0.05] hover:bg-neutral-800/70 hover:border-white/[0.15]"
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2 mb-1">
                        <span className="font-bold text-xs text-white truncate">{other.career_name}</span>
                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-white/[0.06] text-neutral-300">
                          {other.university_short}
                        </span>
                      </div>

                      <div className="flex items-center justify-between text-xs font-mono pt-2 border-t border-white/[0.04]">
                        <span className="text-neutral-400">Pond: {other.weighted_score.toFixed(1)}</span>
                        <span className={`font-bold ${oTheme.text}`}>
                          {other.probability.toFixed(1)}% ({other.category})
                        </span>
                      </div>
                    </button>
                  )
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default CruchAdmissionSimulator
