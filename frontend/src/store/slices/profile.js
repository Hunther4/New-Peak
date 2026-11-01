import { api } from "../../api/client"

export const createProfileSlice = (set, get) => ({
  // State
  profile: null,
  profileLoading: true,

  // Actions
  fetchProfile: async () => {
    // Instant load from localStorage cache
    const cached = localStorage.getItem("peak_profile")
    if (cached) {
      try {
        const parsed = JSON.parse(cached)
        if (parsed?.name) {
          localStorage.setItem("peak_user_name", parsed.name.trim())
        }
        set({ profile: parsed, profileLoading: false })
        // Sync with backend in background (don't await)
        api.profile.get().then(profile => {
          if (profile) {
            set({ profile })
            localStorage.setItem("peak_profile", JSON.stringify(profile))
            localStorage.setItem("peak_user_name", profile.name.trim())
          } else {
            // Backend doesn't have a profile — clear stale cache
            localStorage.removeItem("peak_profile")
            localStorage.removeItem("peak_user_name")
            set({ profile: null })
          }
        }).catch(() => {})
        return parsed
      } catch {
        // JSON parse failed — fall through to API fetch
      }
    }
    // First time — fetch from API
    try {
      const profile = await api.profile.get()
      if (profile) {
        localStorage.setItem("peak_profile", JSON.stringify(profile))
      }
      set({ profile, profileLoading: false })
      return profile
    } catch {
      set({ profileLoading: false })
      return null
    }
  },

  saveProfile: async (name, age) => {
    localStorage.setItem("peak_user_name", name.trim())
    const profile = await api.profile.save({ name: name.trim(), age })
    set({ profile })
    localStorage.setItem("peak_profile", JSON.stringify(profile))
    return profile
  },

  logoutProfile: () => {
    localStorage.removeItem("peak_profile")
    localStorage.removeItem("peak_user_name")
    set({ profile: null })
  },

  uploadAvatar: async (file) => {
    const result = await api.profile.uploadAvatar(file)
    const updated = { ...get().profile, avatar_url: result.avatar_url }
    set({ profile: updated })
    localStorage.setItem("peak_profile", JSON.stringify(updated))
    return result
  }
})