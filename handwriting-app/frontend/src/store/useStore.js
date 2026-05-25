import { create } from 'zustand'

export const MODELS = [
  {
    id: 'diffusionpen',
    name: 'DiffusionPen',
    tag: 'Diffusion',
    description: 'Best quality. Latent diffusion with style encoder.',
  },
  {
    id: 'ganwriting',
    name: 'GANwriting',
    tag: 'GAN',
    description: 'Faster generation. Good for quick drafts.',
  },
  {
    id: 'wordstylist',
    name: 'WordStylist',
    tag: 'Diffusion',
    description: 'High diversity and style variation.',
  },
]

const useStore = create((set) => ({
  currentStep: 1,
  sessionId: null,
  jobId: null,
  selectedModel: 'diffusionpen',
  sampleFiles: [],
  inputText: '',
  pageCount: 1,
  jobStatus: null,
  jobMessage: '',
  jobProgress: 0,
  results: null,
  compareResults: null,
  activeCompareModel: null,
  previewPage: 0,
  error: null,

  setStep: (step) => set({ currentStep: step }),
  setSessionId: (id) => set({ sessionId: id }),
  setJobId: (id) =>
    set({
      jobId: id,
      jobStatus: 'pending',
      jobMessage: 'Queued',
      jobProgress: 0,
      results: null,
      compareResults: null,
      activeCompareModel: null,
      previewPage: 0,
    }),
  setModel: (model) => set({ selectedModel: model }),
  setSamples: (files) => set({ sampleFiles: files }),
  setText: (text) => set({ inputText: text }),
  setPageCount: (n) => set({ pageCount: n }),
  updateJobStatus: (payload) =>
    set({
      jobStatus: payload.status,
      jobMessage: payload.message ?? '',
      jobProgress: payload.progress ?? 0,
    }),
  setResults: (results, compareResults = null) =>
    set({ results, compareResults, jobStatus: 'done' }),
  setActiveCompareModel: (model) => set({ activeCompareModel: model }),
  setPreviewPage: (page) => set({ previewPage: page }),
  setError: (error) => set({ error }),
  resetAll: () =>
    set({
      currentStep: 1,
      sessionId: null,
      jobId: null,
      selectedModel: 'diffusionpen',
      sampleFiles: [],
      inputText: '',
      pageCount: 1,
      jobStatus: null,
      jobMessage: '',
      jobProgress: 0,
      results: null,
      compareResults: null,
      activeCompareModel: null,
      previewPage: 0,
      error: null,
    }),
}))

export default useStore
