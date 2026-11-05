import { api } from "../../api/client"

export const createProfileSlice = (set, get) => ({
  // State
  profile: null,
  profileLoading: true,

  // Actions
  fetchProfile: async () => {
    // Source of truth is the backend (scoped to the caller's principal).
    // No localStorage cache: a stale cached profile could leak one user's
    // name into another session (rancio). See SECURITY_AUDIT_HOTFIX.
    set({ profileLoading: true })
    try {
      const profile = await api.profile.get()
      if (profile && profile.name?.trim().toLowerCase() !== "invitado") {
        set({ profile, profileLoading: false })
        return profile
      }
      set({ profile: null, profileLoading: false })
      return null
    } catch {
      set({ profileLoading: false })
      return null
    }
  },

  saveProfile: async (name, age) => {
    const profile = await api.profile.save({ name: name.trim(), age })
    set({ profile })
    return profile
  },

  logoutProfile: () => {
    set({ profile: null })
  },

  uploadAvatar: async (file) => {
    const result = await api.profile.uploadAvatar(file)
    const updated = { ...get().profile, avatar_url: result.avatar_url }
    set({ profile: updated })
    return result
  }
})