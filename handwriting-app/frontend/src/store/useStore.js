import { create } from 'zustand'

export const MODELS = [
  {
    id: 'diffusionpen',
    tag: 'DIFFUSION',
    name: 'DiffusionPen',
    description:
      'Best quality. Latent diffusion with style encoder. Learns your exact handwriting from 5 samples.',
    sampleMode: 'flexible',
    minSamples: 5,
    maxSamples: 10,
    sampleHint:
      'Upload or draw 5–10 word samples. Canvas drawings work well with this model.',
  },
  {
    id: 'wordstylist',
    tag: 'AUTOREGRESSIVE',
    name: 'Emuru',
    description:
      'CVPR 2025. T5 + VAE · zero-shot from one clear photo.',
    sampleMode: 'photo',
    minSamples: 1,
    maxSamples: 5,
    sampleHint:
      'Zero-shot: one clear pen-on-paper photo is enough. A page with a few words is fine — we auto-crop a style word. Prefer dark ink on white; avoid blank canvas draws.',
  },
]

export function getModelConfig(modelId) {
  return MODELS.find((m) => m.id === modelId) || MODELS[0]
}

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
  resultMeta: null,
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
      resultMeta: null,
      activeCompareModel: null,
      previewPage: 0,
    }),
  setModel: (model) =>
    set((state) => {
      if (model === state.selectedModel) return { selectedModel: model }
      // Changing model invalidates prior samples/session
      return {
        selectedModel: model,
        sampleFiles: [],
        sessionId: null,
        jobId: null,
        jobStatus: null,
        jobMessage: '',
        jobProgress: 0,
        results: null,
        compareResults: null,
        resultMeta: null,
        activeCompareModel: null,
        previewPage: 0,
      }
    }),
  setSamples: (files) => set({ sampleFiles: files }),
  setText: (text) => set({ inputText: text }),
  setPageCount: (n) => set({ pageCount: n }),
  updateJobStatus: (payload) =>
    set({
      jobStatus: payload.status,
      jobMessage: payload.message ?? '',
      jobProgress: payload.progress ?? 0,
    }),
  setResults: (results, compareResults = null, resultMeta = null) =>
    set({ results, compareResults, resultMeta, jobStatus: 'done' }),
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
      resultMeta: null,
      activeCompareModel: null,
      previewPage: 0,
      error: null,
    }),
}))

export default useStore
