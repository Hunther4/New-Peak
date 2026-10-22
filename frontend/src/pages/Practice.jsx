import { useEffect, useCallback, Suspense, lazy, useRef, useState } from "react"
import { useParams, useSearchParams, useNavigate } from "react-router"
import { useStore } from "../store/store"
import { useGameBlocker, ExitGamePrompt } from "../hooks/useGameBlocker.jsx"
import Spinner from "../components/ui/Spinner"

// Lazy-load game components — each becomes its own chunk
const MemoryGame = lazy(() => import("../components/MemoryGame"))
const MathThinkingGame = lazy(() => import("../components/MathThinkingGame"))
const DualNBackGame = lazy(() => import("../components/DualNBackGame"))
const IQPracticeGame = lazy(() => import("../components/IQPracticeGame"))

// Game route map — adding a new game = 1 line here + 1 component file
const GAME_COMPONENTS = {
  memory_number: { load: () => MemoryGame, needsSkillId: true },
  problem_set: { load: () => MathThinkingGame, needsSkillId: true },
  math_thinking: { load: () => MathThinkingGame, needsSkillId: true },
  dual_n_back: { load: () => DualNBackGame, needsSkillId: false },
  iq_practice: { load: () => IQPracticeGame, needsSkillId: true },
}

function GameLoading() {
  return (
    <div className="min-h-screen bg-neutral-950 flex items-center justify-center">
      <div className="text-center">
        <Spinner size="lg" className="mx-auto mb-3" />
        <p className="text-xs text-neutral-500 uppercase tracking-wider">Cargando juego...</p>
      </div>
    </div>
  )
}

export default function Practice() {
  const { gameType } = useParams()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { fetchSummary, fetchTimeline, skills, fetchSkills } = useStore()
  const gameAreaRef = useRef(null)
  const [hasInteracted, setHasInteracted] = useState(false)

  const skillIdParam = searchParams.get("skillId")

  // Auto-fetch skills if not loaded and needed
  useEffect(() => {
    if (!skillIdParam && fetchSkills && (!skills || skills.length === 0)) {
      fetchSkills()
    }
  }, [skillIdParam, fetchSkills, skills])

  const route = GAME_COMPONENTS[gameType]

  // Resolve skillId from query param or match by gameType/slug
  const resolvedSkillId = skillIdParam
    ? parseInt(skillIdParam, 10)
    : (skills?.find(
        (s) => s.skill_type === gameType || s.slug === gameType?.replace(/_/g, "-")
      )?.id || null)

  // Invalid game type → redirect to dashboard
  useEffect(() => {
    if (!route) {
      navigate("/", { replace: true })
    }
  }, [route, navigate])

  // Track first interaction inside the game area (click/touch/keypress)
  useEffect(() => {
    if (hasInteracted) return
    const handler = (e) => {
      // Only activate after user interacts inside the game area
      if (gameAreaRef.current?.contains(e.target)) {
        setHasInteracted(true)
      }
    }
    document.addEventListener("click", handler, { capture: true })
    document.addEventListener("keydown", handler, { capture: true })
    return () => {
      document.removeEventListener("click", handler, { capture: true })
      document.removeEventListener("keydown", handler, { capture: true })
    }
  }, [hasInteracted])

  // Block navigation only after user has started interacting with the game
  const { showPrompt, confirmNavigation, cancelNavigation } = useGameBlocker(hasInteracted)

  const handleClose = useCallback(() => {
    fetchSummary()
    fetchTimeline()
    navigate("/")
  }, [fetchSummary, fetchTimeline, navigate])

  if (!route) return null

  const { needsSkillId } = route

  // If game needs skillId and skills are loaded but no matching skill found → redirect
  if (needsSkillId && !resolvedSkillId && skills && skills.length > 0) {
    navigate("/", { replace: true })
    return null
  }

  // If game needs skillId and still waiting for skills to fetch → show GameLoading
  if (needsSkillId && !resolvedSkillId) {
    return <GameLoading />
  }

  const GameComponent = route.load()

  return (
    <div ref={gameAreaRef}>
      <Suspense fallback={<GameLoading />}>
        <GameComponent
          skillId={needsSkillId ? resolvedSkillId : null}
          onClose={handleClose}
        />
      </Suspense>

      {/* Exit confirmation — only shown when navigation is blocked */}
      <ExitGamePrompt
        show={showPrompt}
        onConfirm={confirmNavigation}
        onCancel={cancelNavigation}
      />
    </div>
  )
}
