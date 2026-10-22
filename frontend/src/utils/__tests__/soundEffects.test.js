import { describe, it, expect, beforeEach, vi, afterEach } from "vitest"
import {
  isSoundMuted,
  setSoundMuted,
  toggleSoundMute,
  isMuted,
  setMuted,
  toggleMute,
  playClickSound,
  playSelectTap,
  playSuccessSound,
  playSuccessChime,
  playErrorSound,
  playErrorTone,
  playStreakSound,
  playStreakCelebration,
  playHaptic,
  _resetAudioContextForTesting,
} from "../soundEffects"

describe("soundEffects utility", () => {
  let mockOscillator
  let mockGain
  let mockAudioContext

  beforeEach(() => {
    localStorage.clear()
    _resetAudioContextForTesting()

    mockOscillator = {
      type: "sine",
      frequency: {
        setValueAtTime: vi.fn(),
        exponentialRampToValueAtTime: vi.fn(),
      },
      connect: vi.fn(),
      start: vi.fn(),
      stop: vi.fn(),
    }

    mockGain = {
      gain: {
        setValueAtTime: vi.fn(),
        linearRampToValueAtTime: vi.fn(),
        exponentialRampToValueAtTime: vi.fn(),
      },
      connect: vi.fn(),
    }

    mockAudioContext = {
      currentTime: 10,
      state: "running",
      destination: {},
      createOscillator: vi.fn(() => ({ ...mockOscillator })),
      createGain: vi.fn(() => ({ ...mockGain })),
      resume: vi.fn().mockResolvedValue(undefined),
    }

    // Assign mock AudioContext class to window
    window.AudioContext = class {
      constructor() {
        return mockAudioContext
      }
    }
    window.webkitAudioContext = window.AudioContext
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe("Mute state management", () => {
    it("defaults to unmuted (false)", () => {
      expect(isSoundMuted()).toBe(false)
      expect(isMuted()).toBe(false)
    })

    it("saves muted state in localStorage under peak_sound_muted", () => {
      setSoundMuted(true)
      expect(localStorage.getItem("peak_sound_muted")).toBe("true")
      expect(isSoundMuted()).toBe(true)
      expect(isMuted()).toBe(true)

      setMuted(false)
      expect(localStorage.getItem("peak_sound_muted")).toBe("false")
      expect(isSoundMuted()).toBe(false)
    })

    it("toggles mute state correctly", () => {
      expect(toggleSoundMute()).toBe(true)
      expect(isSoundMuted()).toBe(true)

      expect(toggleMute()).toBe(false)
      expect(isSoundMuted()).toBe(false)
    })

    it("dispatches custom event on mute state change", () => {
      const listener = vi.fn()
      window.addEventListener("peak-sound-mute-change", listener)

      setSoundMuted(true)
      expect(listener).toHaveBeenCalled()

      window.removeEventListener("peak-sound-mute-change", listener)
    })
  })

  describe("Acoustic synthesis playback", () => {
    it("plays click sound when unmuted", () => {
      setSoundMuted(false)
      playClickSound()
      expect(mockAudioContext.createOscillator).toHaveBeenCalled()
      expect(mockAudioContext.createGain).toHaveBeenCalled()
    })

    it("playSelectTap aliases playClickSound", () => {
      setSoundMuted(false)
      playSelectTap()
      expect(mockAudioContext.createOscillator).toHaveBeenCalled()
    })

    it("does not play sounds when muted", () => {
      setSoundMuted(true)
      playClickSound()
      playSuccessSound()
      playErrorSound()
      playStreakSound(3)
      expect(mockAudioContext.createOscillator).not.toHaveBeenCalled()
    })

    it("plays bright success sound with multiple notes", () => {
      setSoundMuted(false)
      playSuccessSound()
      // Pentatonic 5 notes -> 5 oscillators
      expect(mockAudioContext.createOscillator).toHaveBeenCalledTimes(5)
    })

    it("playSuccessChime aliases playSuccessSound", () => {
      setSoundMuted(false)
      playSuccessChime()
      expect(mockAudioContext.createOscillator).toHaveBeenCalledTimes(5)
    })

    it("plays warm non-punitive error sound", () => {
      setSoundMuted(false)
      playErrorSound()
      expect(mockAudioContext.createOscillator).toHaveBeenCalledTimes(2)
    })

    it("playErrorTone aliases playErrorSound", () => {
      setSoundMuted(false)
      playErrorTone()
      expect(mockAudioContext.createOscillator).toHaveBeenCalledTimes(2)
    })

    it("plays streak arpeggio scaling with count", () => {
      setSoundMuted(false)
      // count 3
      playStreakSound(3)
      expect(mockAudioContext.createOscillator).toHaveBeenCalledTimes(5)

      mockAudioContext.createOscillator.mockClear()
      // count 5
      playStreakSound(5)
      expect(mockAudioContext.createOscillator).toHaveBeenCalledTimes(6)

      mockAudioContext.createOscillator.mockClear()
      // count 10
      playStreakCelebration(10)
      expect(mockAudioContext.createOscillator).toHaveBeenCalledTimes(7)
    })
  })

  describe("Haptic feedback", () => {
    it("calls navigator.vibrate when available", () => {
      navigator.vibrate = vi.fn()
      playHaptic(30)
      expect(navigator.vibrate).toHaveBeenCalledWith(30)
    })
  })
})
