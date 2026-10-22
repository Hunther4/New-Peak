/**
 * Native Web Audio API Sound Effects & Haptics Engine for Peak PAES.
 * Zero external dependencies. Uses synthesizers to avoid audio asset loading overhead.
 */

let audioCtx = null

function getAudioContext() {
  if (typeof window === "undefined") return null
  try {
    if (!audioCtx) {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext
      if (AudioContextClass) {
        audioCtx = new AudioContextClass()
      }
    }
    if (audioCtx && audioCtx.state === "suspended") {
      audioCtx.resume().catch(() => {})
    }
    return audioCtx
  } catch {
    return null
  }
}

export function _resetAudioContextForTesting() {
  audioCtx = null
}

export function isSoundMuted() {
  if (typeof window === "undefined" || !window.localStorage) return false
  return localStorage.getItem("peak_sound_muted") === "true"
}

export function setSoundMuted(muted) {
  if (typeof window === "undefined" || !window.localStorage) return
  localStorage.setItem("peak_sound_muted", muted ? "true" : "false")
  try {
    window.dispatchEvent(new CustomEvent("peak-sound-mute-change", { detail: { muted: !!muted } }))
  } catch {
    // Ignore storage access restrictions
  }
}

export function toggleSoundMute() {
  const current = isSoundMuted()
  setSoundMuted(!current)
  return !current
}

// Ergonomic aliases
export const isMuted = isSoundMuted
export const setMuted = setSoundMuted
export const toggleMute = toggleSoundMute

/**
 * Triggers device haptic feedback if supported (mobile/tablets).
 */
export function playHaptic(pattern = 20) {
  if (typeof window !== "undefined" && typeof navigator !== "undefined" && navigator.vibrate) {
    try {
      navigator.vibrate(pattern)
    } catch {
      // Ignore vibration error on unsupported devices
    }
  }
}

/**
 * Subtle tactile acoustic tap / click when alternating alternatives (A, B, C, D).
 */
export function playClickSound() {
  if (isSoundMuted()) return
  const ctx = getAudioContext()
  if (!ctx) return

  try {
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()

    osc.type = "sine"
    osc.frequency.setValueAtTime(600, ctx.currentTime)
    osc.frequency.exponentialRampToValueAtTime(150, ctx.currentTime + 0.035)

    gain.gain.setValueAtTime(0.08, ctx.currentTime)
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.035)

    osc.connect(gain)
    gain.connect(ctx.destination)

    osc.start(ctx.currentTime)
    osc.stop(ctx.currentTime + 0.035)
  } catch {}
}

// Backward-compatible alias
export const playSelectTap = playClickSound

/**
 * Bright ascending major pentatonic chord when answering correctly.
 * Pentatonic scale notes: C5 (523.25), D5 (587.33), E5 (659.25), G5 (783.99), C6 (1046.50).
 */
export function playSuccessSound() {
  playHaptic([25, 40, 30])
  if (isSoundMuted()) return
  const ctx = getAudioContext()
  if (!ctx) return

  try {
    const notes = [523.25, 587.33, 659.25, 783.99, 1046.50] // C5, D5, E5, G5, C6 (major pentatonic)
    notes.forEach((freq, idx) => {
      const startTime = ctx.currentTime + idx * 0.065
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()

      osc.type = "triangle"
      osc.frequency.setValueAtTime(freq, startTime)

      gain.gain.setValueAtTime(0.001, startTime)
      gain.gain.linearRampToValueAtTime(0.12, startTime + 0.02)
      gain.gain.exponentialRampToValueAtTime(0.0001, startTime + 0.35)

      osc.connect(gain)
      gain.connect(ctx.destination)

      osc.start(startTime)
      osc.stop(startTime + 0.36)
    })
  } catch {}
}

// Backward-compatible alias
export const playSuccessChime = playSuccessSound

/**
 * Soft, pedagogical warm chime on error (descending soft tone D4 -> Bb3).
 * Non-punitive and gentle to maintain motivation.
 */
export function playErrorSound() {
  playHaptic([50, 40, 60])
  if (isSoundMuted()) return
  const ctx = getAudioContext()
  if (!ctx) return

  try {
    const notes = [293.66, 233.08] // D4, Bb3
    notes.forEach((freq, idx) => {
      const startTime = ctx.currentTime + idx * 0.12
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()

      osc.type = "sine"
      osc.frequency.setValueAtTime(freq, startTime)

      gain.gain.setValueAtTime(0.001, startTime)
      gain.gain.linearRampToValueAtTime(0.08, startTime + 0.03)
      gain.gain.exponentialRampToValueAtTime(0.0001, startTime + 0.28)

      osc.connect(gain)
      gain.connect(ctx.destination)

      osc.start(startTime)
      osc.stop(startTime + 0.29)
    })
  } catch {}
}

// Backward-compatible alias
export const playErrorTone = playErrorSound

/**
 * Streak milestone flourish arpeggio (3, 5, 10 in a row).
 * Scales in brilliance based on count.
 */
export function playStreakSound(count = 3) {
  if (isSoundMuted()) return
  const ctx = getAudioContext()
  if (!ctx) return

  try {
    let notes = [523.25, 659.25, 783.99, 1046.50] // Base: C5, E5, G5, C6
    let stepTime = 0.06
    let noteDuration = 0.4

    if (count >= 10) {
      // 10+ streak: Golden extended arpeggio spanning octaves
      notes = [523.25, 659.25, 783.99, 987.77, 1046.50, 1318.51, 1567.98] // C5, E5, G5, B5, C6, E6, G6
      stepTime = 0.045
      noteDuration = 0.55
      playHaptic([30, 40, 30, 40, 80])
    } else if (count >= 5) {
      // 5+ streak: Vibrant 6-note arpeggio
      notes = [523.25, 659.25, 783.99, 880.00, 1046.50, 1318.51] // C5, E5, G5, A5, C6, E6
      stepTime = 0.055
      noteDuration = 0.45
      playHaptic([30, 40, 30, 50])
    } else {
      // 3+ streak: Energetic 5-note ascending fanfare
      notes = [523.25, 659.25, 783.99, 1046.50, 1318.51]
      stepTime = 0.06
      noteDuration = 0.4
      playHaptic([25, 35, 45])
    }

    notes.forEach((freq, idx) => {
      const startTime = ctx.currentTime + idx * stepTime
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()

      osc.type = "triangle"
      osc.frequency.setValueAtTime(freq, startTime)

      gain.gain.setValueAtTime(0.001, startTime)
      gain.gain.linearRampToValueAtTime(0.14, startTime + 0.02)
      gain.gain.exponentialRampToValueAtTime(0.0001, startTime + noteDuration)

      osc.connect(gain)
      gain.connect(ctx.destination)

      osc.start(startTime)
      osc.stop(startTime + noteDuration + 0.01)
    })
  } catch {}
}

// Backward-compatible alias
export const playStreakCelebration = playStreakSound
