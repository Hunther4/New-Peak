import React, { useState, useEffect, useMemo, useCallback } from "react"
import { api } from "../../api/client"

export function CruchAdmissionSimulator() {
  const [careers, setCareers] = useState([])
  const [loadingCareers, setLoadingCareers] = useState(true)
  const [selectedCareerId, setSelectedCareerId] = useState("medicina-udec")
  const [selectedUniversityFilter, setSelectedUniversityFilter] = useState("CONCEPCION")
  const [selectedCampusFilter, setSelectedCampusFilter] = useState("ALL")
  const [searchTerm, setSearchTerm] = useState("")

  // Sincronización Nota (4.00 - 7.00) y Puntaje NEM oficial DEMRE (100 - 1000)
  // Fórmula DEMRE Grupo A: Puntaje = 100 + (Nota - 4.0) * 300
  const gradeFromNem = (score) => Number((4.0 + (Math.max(100, Math.min(1000, score)) - 100) / 300).toFixed(2))
  const nemFromGrade = (grade) => Math.round(100 + (Math.max(4.0, Math.min(7.0, grade)) - 4.0) * 300)

  // Factores académicos (NEM, Ranking) y pruebas PAES
  const [nem, setNem] = useState(820)
  const [nemGrade, setNemGrade] = useState(gradeFromNem(820)) // 6.40
  const [ranking, setRanking] = useState(850)
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

  // Filtrado de carreras por universidad, campus y búsqueda textual
  const filteredCareers = useMemo(() => {
    let list = careers
    if (selectedUniversityFilter === "CONCEPCION") {
      list = list.filter(
        (c) =>
          ["UdeC", "UBB", "UCSC"].includes(c.university_short) ||
          c.city === "Concepción" ||
          c.region === "Biobío"
      )
    } else if (selectedUniversityFilter !== "ALL") {
      list = list.filter((c) => c.university_short === selectedUniversityFilter)
    }

    if (selectedCampusFilter !== "ALL") {
      list = list.filter((c) => (c.campus || "").toLowerCase().includes(selectedCampusFilter.toLowerCase()))
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
  }, [careers, selectedUniversityFilter, selectedCampusFilter, searchTerm])

  const selectedCareer = useMemo(() => {
    return careers.find((c) => c.id === selectedCareerId) || filteredCareers[0] || careers[0]
  }, [careers, selectedCareerId, filteredCareers])

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
        icon: "🟢",
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
        icon: "🟡",
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
      icon: "🔴",
    }
  }

  const probTheme = getProbabilityTheme(
    simulation?.category || "Competitiva",
    simulation?.probability || 50
  )

  const universityPills = [
    { id: "CONCEPCION", label: "📍 Zona Concepción (Biobío)" },
    { id: "UdeC", label: "U. de Concepción" },
    { id: "UBB", label: "U. del Bío-Bío" },
    { id: "UCSC", label: "UCSC" },
    { id: "ALL", label: "Todas las Universidades" },
    { id: "UCH", label: "U. de Chile" },
    { id: "PUC", label: "Católica (PUC)" },
    { id: "USACH", label: "USACH" },
    { id: "UTFSM", label: "Santa María" },
  ]

  return (
    <div className="space-y-8 animate-fade-in pb-12">
      {/* Encabezado Principal */}
      <div className="p-6 md:p-8 rounded-3xl bg-neutral-900/70 border border-white/[0.08] backdrop-blur-xl shadow-2xl relative overflow-hidden">
        <div className="absolute -right-16 -top-16 w-64 h-64 bg-sky-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 relative z-10">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="text-2xl">🏛️</span>
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
                <span>🎯</span> Carrera & Universidad Objetivo
              </h3>
              {selectedCareer?.requires_m2 && (
                <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-md bg-amber-500/20 text-amber-300 border border-amber-500/30">
                  Exige M2
                </span>
              )}
            </div>

            {/* Filtro de Universidades */}
            <div className="flex flex-wrap gap-1.5">
              {universityPills.map((u) => (
                <button
                  key={u.id}
                  onClick={() => setSelectedUniversityFilter(u.id)}
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

            {/* Buscador de Carreras y Filtro de Campus */}
            <div className="space-y-3">
              <div className="relative">
                <input
                  type="text"
                  placeholder="🔍 Buscar carrera (ej. Aeroespacial, Medicina, Derecho, 13086)..."
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
                    ✕
                  </button>
                )}
              </div>

              {/* Campus Pills para UdeC / Concepción */}
              {["CONCEPCION", "UdeC", "UBB"].includes(selectedUniversityFilter) && (
                <div className="flex items-center gap-1.5 overflow-x-auto text-[10px] font-mono">
                  <span className="text-neutral-500">Campus:</span>
                  {[
                    { id: "ALL", label: "Todos" },
                    { id: "Concepción", label: "Concepción" },
                    { id: "Chillán", label: "Chillán" },
                    { id: "Los Ángeles", label: "Los Ángeles" },
                  ].map((cp) => (
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

              {/* Selector de Carrera */}
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
                  {filteredCareers.map((c) => (
                    <option key={c.id} value={c.id} className="bg-neutral-900 text-white">
                      {c.name} ({c.campus}) — {c.university_short} • Cód. {c.code || "---"} (Corte '26: {c.cutoffs["2026"]} pts)
                    </option>
                  ))}
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
                <div className="text-neutral-400 text-[11px]">
                  🏛️ {selectedCareer.university} • {selectedCareer.campus}
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
              </div>
            )}
          </div>
        </div>

        {/* Columna Derecha: Controles de Puntajes (NEM, Ranking, Pruebas) (7 cols) */}
        <div className="lg:col-span-7 space-y-6">
          <div className="p-6 rounded-3xl bg-neutral-900/60 border border-white/[0.08] backdrop-blur-xl shadow-xl space-y-6">
            <h3 className="text-sm font-black uppercase tracking-wider text-white flex items-center justify-between">
              <span className="flex items-center gap-2">
                <span>📊</span> Tus Puntajes Estimados o Simulados
              </span>
              <span className="text-[11px] font-mono text-neutral-500 font-normal">Escala DEMRE 100 - 1000</span>
            </h3>

            {/* Factores Escolares: NEM y Ranking */}
            <div className="p-4 rounded-2xl bg-neutral-950/60 border border-white/[0.08] space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-white/[0.06]">
                <div className="space-y-0.5">
                  <div className="text-xs font-bold text-white flex items-center gap-1.5">
                    <span>🎓</span> Trayectoria Escolar (DEMRE Grupo A)
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
                      <div className="text-[10px] text-neutral-400 font-mono">Fórmula: 100 + (Nota - 4.0) × 300</div>
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
                    <span>5.50 (550 pts)</span>
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
                    <span>📐</span> Competencia Matemática 1 (M1)
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
                    <span>📖</span> Competencia Lectora
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
                    <span>🔬</span> Competencia Matemática 2 (M2)
                    {selectedCareer?.requires_m2 && (
                      <span className="text-[10px] font-mono text-amber-400">*(Requerida)*</span>
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
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                <div className="space-y-1.5">
                  <div className="flex justify-between items-center text-xs">
                    <span className="font-bold text-neutral-300">Ciencias (Bio/Fís/Quím)</span>
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

                <div className="space-y-1.5">
                  <div className="flex justify-between items-center text-xs">
                    <span className="font-bold text-neutral-300">Historia y Cs. Sociales</span>
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
                  <span>🎯</span> Brecha a la Meta de Admisión
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
                          Cumplido ✓
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
                              ⚠️ Excede 1000 pts si intentas compensar todo solo con esta prueba. Conviene distribuir esfuerzos.
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
                  <span className="text-lg">💡</span>
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
                    <span>📋</span> Pronóstico en otras Carreras CRUCH
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
