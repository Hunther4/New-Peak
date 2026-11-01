import { api } from "../../api/client"

export const createPaesSlice = (set, get) => ({
  paesSessionId: null,
  paesSubtopic: null,
  paesQuestions: [],
  paesCurrentIndex: 0,
  paesActiveQuestion: null,
  paesSelectedOption: null,
  paesConfidence: 3,
  paesLastResult: null,
  paesFsrsStatus: null,
  paesSubtopicsList: [],
  paesSocraticHints: [],
  paesLoading: false,
  paesError: null,

  // --- Multidisciplinary PAES Subjects ---
  paesSubjects: [],
  paesActiveSubject: "M1",

  // --- Exam Simulation State ---
  paesExamActive: false,
  paesExamTimeLimitMinutes: 32,
  paesExamAnswers: {}, // { [qId]: { selectedOption, timeSpentSeconds } }
  paesExamFlags: [], // [qId]
  paesExamResults: null,

  // --- Cuaderno de Errores & Revancha ---
  paesErrorNotebook: { total_errors: 0, by_subject: {}, by_mistake_cause: {}, items: [] },
  paesErrorVault: { total_errors: 0, by_subject: {}, by_distractor_type: {}, by_mistake_cause: {}, items: [] },
  paesActiveVariant: null,
  paesVariantLoading: false,

  fetchPaesSubjects: async () => {
    try {
      set({ paesLoading: true, paesError: null })
      const data = await api.paes.getSubjects()
      set({ paesSubjects: data.subjects || [], paesLoading: false })
      return data.subjects
    } catch (err) {
      set({ paesError: err.message, paesLoading: false })
    }
  },

  setPaesActiveSubject: async (code) => {
    set({ paesActiveSubject: code })
    await get().fetchPaesSubtopics(1, code)
  },

  fetchPaesFsrsStatus: async (userId = 1, subjectCode = null) => {
    try {
      set({ paesLoading: true, paesError: null })
      const targetSubject = subjectCode || get().paesActiveSubject || "M1"
      const data = await api.paes.getFsrsStatus(userId, targetSubject)
      set({ paesFsrsStatus: data, paesLoading: false })
      return data
    } catch (err) {
      set({ paesError: err.message, paesLoading: false })
    }
  },

  fetchPaesSubtopics: async (userId = 1, subjectCode = null) => {
    try {
      set({ paesLoading: true, paesError: null })
      const targetSubject = subjectCode || get().paesActiveSubject || "M1"
      const data = await api.paes.getCurriculumSubtopics(userId, targetSubject)
      set({ paesSubtopicsList: data.subtopics, paesLoading: false })
      return data.subtopics
    } catch (err) {
      set({ paesError: err.message, paesLoading: false })
    }
  },

  loadErrorVault: async (userId = 1, subjectCode = null) => {
    try {
      set({ paesLoading: true, paesError: null })
      const targetSubject = subjectCode || get().paesActiveSubject || null
      const data = await api.paes.getErrorVault(userId, targetSubject)
      set({
        paesErrorVault: data,
        paesErrorNotebook: data,
        paesLoading: false,
      })
      return data
    } catch (err) {
      set({ paesError: err.message, paesLoading: false })
    }
  },

  fetchPaesErrorNotebook: async (subjectCode = null) => {
    try {
      set({ paesLoading: true, paesError: null })
      const targetSubject = subjectCode || get().paesActiveSubject || null
      const data = await api.paes.getErrorVault ? await api.paes.getErrorVault(1, targetSubject) : await api.paes.getErrorNotebook(targetSubject)
      set({
        paesErrorNotebook: data,
        paesErrorVault: data,
        paesLoading: false,
      })
      return data
    } catch (err) {
      set({ paesError: err.message, paesLoading: false })
    }
  },

  fetchQuestionVariant: async (questionId, seed = null) => {
    try {
      set({ paesVariantLoading: true, paesError: null })
      const data = await api.paes.getQuestionVariant(questionId, seed)
      set({ paesActiveVariant: data, paesVariantLoading: false })
      return data
    } catch (err) {
      set({ paesError: err.message, paesVariantLoading: false })
      throw err
    }
  },

  clearQuestionVariant: () => set({ paesActiveVariant: null, paesVariantLoading: false }),

  startRevengeSession: async (questionCount = 10, subjectCode = null) => {
    try {
      set({
        paesLoading: true,
        paesError: null,
        paesExamResults: null,
        paesExamAnswers: {},
        paesExamFlags: [],
        paesSocraticHints: [],
        paesLastResult: null,
        paesExamActive: false,
      })
      const targetSubject = subjectCode || get().paesActiveSubject || "M1"
      let data
      try {
        data = await api.paes.startRevengeSession(questionCount, targetSubject, 1)
      } catch {
        data = await api.paes.startStudySession("REVENGE", null, questionCount, targetSubject)
      }
      set({
        paesSessionId: data.session_id,
        paesSubtopic: `Sesión de Revancha (${data.subject_name || targetSubject})`,
        paesQuestions: data.questions,
        paesCurrentIndex: 0,
        paesActiveQuestion: data.questions[0] || null,
        paesSelectedOption: null,
        paesLoading: false,
      })
      return data
    } catch (err) {
      set({ paesError: err.message, paesLoading: false })
    }
  },

  startPaesSession: async (sessionMode = "PRACTICE", subtopicSlug = null, questionCount = null, subjectCode = null) => {
    try {
      set({ paesLoading: true, paesError: null, paesSocraticHints: [], paesLastResult: null, paesExamActive: false })
      const targetSubject = subjectCode || get().paesActiveSubject || "M1"
      const data = await api.paes.startStudySession(sessionMode, subtopicSlug, questionCount, targetSubject)
      set({
        paesSessionId: data.session_id,
        paesSubtopic: data.subtopic,
        paesQuestions: data.questions,
        paesCurrentIndex: 0,
        paesActiveQuestion: data.questions[0] || null,
        paesSelectedOption: null,
        paesLoading: false,
      })
      return data
    } catch (err) {
      set({ paesError: err.message, paesLoading: false })
    }
  },

  // Start an official DEMRE mock test
  startPaesExam: async (questionCount = 15, subjectCode = null) => {
    try {
      set({
        paesLoading: true,
        paesError: null,
        paesExamResults: null,
        paesExamAnswers: {},
        paesExamFlags: [],
        paesSocraticHints: [],
        paesLastResult: null,
      })
      const targetSubject = subjectCode || get().paesActiveSubject || "M1"
      const data = await api.paes.startStudySession("EXAM", null, questionCount, targetSubject)
      const timeLimit = data.time_limit_minutes || (questionCount >= 60 ? 140 : questionCount >= 30 ? 65 : 32)
      const subtopicDesc = `Simulacro Oficial (${data.subject_name || targetSubject} - ${questionCount} Preguntas)`
      
      const examSessionData = {
        sessionId: data.session_id,
        subtopic: subtopicDesc,
        questions: data.questions,
        currentIndex: 0,
        activeQuestion: data.questions[0] || null,
        timeLimitMinutes: timeLimit,
        subjectCode: targetSubject,
        startedAt: Date.now(),
      }
      try {
        localStorage.setItem("peak_active_exam_state", JSON.stringify(examSessionData))
      } catch {}

      set({
        paesExamActive: true,
        paesSessionId: data.session_id,
        paesSubtopic: subtopicDesc,
        paesQuestions: data.questions,
        paesCurrentIndex: 0,
        paesActiveQuestion: data.questions[0] || null,
        paesExamTimeLimitMinutes: timeLimit,
        paesLoading: false,
      })
      return data
    } catch (err) {
      set({ paesError: err.message, paesLoading: false, paesExamActive: false })
    }
  },

  restoreActiveExamSession: () => {
    try {
      const raw = localStorage.getItem("peak_active_exam_state")
      if (!raw) return false
      const exam = JSON.parse(raw)
      if (!exam || !exam.sessionId || !exam.questions || exam.questions.length === 0) return false

      const backupRaw = localStorage.getItem(`paes_exam_backup_${exam.sessionId}`)
      let answers = {}
      let flags = []
      let secondsRemaining = (exam.timeLimitMinutes || 32) * 60
      if (backupRaw) {
        const backup = JSON.parse(backupRaw)
        if (backup?.answers) answers = backup.answers
        if (backup?.flags) flags = backup.flags
        if (backup?.savedAt && backup?.secondsRemaining !== undefined) {
          const elapsed = Math.floor((Date.now() - backup.savedAt) / 1000)
          secondsRemaining = Math.max(0, backup.secondsRemaining - elapsed)
        }
      }

      if (secondsRemaining <= 1) {
        localStorage.removeItem("peak_active_exam_state")
        localStorage.removeItem(`paes_exam_backup_${exam.sessionId}`)
        return false
      }

      set({
        paesExamActive: true,
        paesSessionId: exam.sessionId,
        paesSubtopic: exam.subtopic,
        paesQuestions: exam.questions,
        paesCurrentIndex: exam.currentIndex || 0,
        paesActiveQuestion: exam.questions[exam.currentIndex || 0] || exam.questions[0],
        paesExamTimeLimitMinutes: exam.timeLimitMinutes || 32,
        paesExamAnswers: answers,
        paesExamFlags: flags,
        paesActiveSubject: exam.subjectCode || get().paesActiveSubject || "M1",
      })
      return true
    } catch {
      return false
    }
  },

  setExamAnswer: (questionId, selectedOption, timeSpentSeconds = 0) => {
    const { paesExamAnswers } = get()
    const current = paesExamAnswers[questionId] || {}
    set({
      paesExamAnswers: {
        ...paesExamAnswers,
        [questionId]: {
          selectedOption,
          timeSpentSeconds: (current.timeSpentSeconds || 0) + timeSpentSeconds,
        },
      },
    })
  },

  toggleExamFlag: (questionId) => {
    const { paesExamFlags } = get()
    const exists = paesExamFlags.includes(questionId)
    set({
      paesExamFlags: exists
        ? paesExamFlags.filter((id) => id !== questionId)
        : [...paesExamFlags, questionId],
    })
  },

  jumpToPaesQuestion: (idx) => {
    const { paesQuestions, paesExamActive } = get()
    if (idx >= 0 && idx < paesQuestions.length) {
      set({
        paesCurrentIndex: idx,
        paesActiveQuestion: paesQuestions[idx],
        paesSelectedOption: null,
      })
      if (paesExamActive) {
        try {
          const raw = localStorage.getItem("peak_active_exam_state")
          if (raw) {
            const parsed = JSON.parse(raw)
            parsed.currentIndex = idx
            parsed.activeQuestion = paesQuestions[idx]
            localStorage.setItem("peak_active_exam_state", JSON.stringify(parsed))
          }
        } catch {}
      }
    }
  },

  finalizePaesExam: async () => {
    const { paesSessionId, paesQuestions, paesExamAnswers, paesActiveSubject } = get()
    if (!paesSessionId) return

    try {
      set({ paesLoading: true, paesError: null })
      const answersList = paesQuestions.map((q) => {
        const recorded = paesExamAnswers[q.id]
        return {
          question_id: q.id,
          selected_option: recorded ? recorded.selectedOption : null,
          time_spent_seconds: recorded ? recorded.timeSpentSeconds : 0,
        }
      })

      const results = await api.paes.finalizeExam(
        paesSessionId,
        answersList,
        paesActiveSubject || "M1"
      )

      try {
        localStorage.removeItem("peak_active_exam_state")
        if (paesSessionId) {
          localStorage.removeItem(`paes_exam_backup_${paesSessionId}`)
        }
      } catch {}
      set({
        paesExamResults: results,
        paesExamActive: false,
        paesLoading: false,
      })
      return results
    } catch (err) {
      set({ paesError: err.message, paesLoading: false })
    }
  },

  exitPaesExam: () => {
    const currentId = get().paesSessionId
    try {
      localStorage.removeItem("peak_active_exam_state")
      if (currentId) {
        localStorage.removeItem(`paes_exam_backup_${currentId}`)
      }
    } catch {}
    set({
      paesExamActive: false,
      paesExamResults: null,
      paesSessionId: null,
      paesQuestions: [],
      paesActiveQuestion: null,
    })
  },

  selectPaesOption: (optKey) => set({ paesSelectedOption: optKey }),
  setPaesConfidence: (val) => set({ paesConfidence: val }),

  submitPaesAttempt: async (timeSpentSeconds = 30) => {
    const { paesSessionId, paesActiveQuestion, paesSelectedOption, paesConfidence } = get()
    if (!paesSessionId || !paesActiveQuestion || !paesSelectedOption) return

    try {
      set({ paesLoading: true, paesError: null })
      const res = await api.paes.submitAttempt({
        session_id: paesSessionId,
        question_id: paesActiveQuestion.id,
        selected_option: paesSelectedOption,
        time_spent_seconds: timeSpentSeconds,
        perceived_confidence: paesConfidence,
      })
      set({
        paesLastResult: res,
        paesLoading: false,
      })
      return res
    } catch (err) {
      set({ paesError: err.message, paesLoading: false })
    }
  },

  nextPaesQuestion: () => {
    const { paesQuestions, paesCurrentIndex } = get()
    const nextIdx = paesCurrentIndex + 1
    if (nextIdx < paesQuestions.length) {
      set({
        paesCurrentIndex: nextIdx,
        paesActiveQuestion: paesQuestions[nextIdx],
        paesSelectedOption: null,
        paesLastResult: null,
        paesSocraticHints: [],
      })
    } else {
      set({
        paesActiveQuestion: null,
        paesLastResult: null,
      })
    }
  },

  requestSocraticHint: async (studentMessage = null) => {
    const { paesSessionId, paesActiveQuestion, paesSocraticHints } = get()
    if (!paesSessionId || !paesActiveQuestion) return

    const nextLevel = paesSocraticHints.length + 1
    try {
      const data = await api.paes.getSocraticHint(
        paesSessionId,
        paesActiveQuestion.id,
        nextLevel,
        studentMessage
      )
      set({
        paesSocraticHints: [...paesSocraticHints, data],
      })
      return data
    } catch (err) {
      set({ paesError: err.message })
    }
  },

  resetPaesSession: () =>
    set({
      paesSessionId: null,
      paesSubtopic: null,
      paesQuestions: [],
      paesCurrentIndex: 0,
      paesActiveQuestion: null,
      paesSelectedOption: null,
      paesLastResult: null,
      paesSocraticHints: [],
      paesError: null,
      paesExamActive: false,
      paesExamResults: null,
    }),
})
