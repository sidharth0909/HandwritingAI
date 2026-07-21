import axios from 'axios'

const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8080'

export const api = axios.create({ baseURL })

export function fileUrl(path) {
  if (!path) return ''
  if (path.startsWith('http')) return path
  return `${baseURL}${path}`
}

export async function uploadSamples(files, sessionId = null, model = null) {
  const form = new FormData()
  files.forEach((file) => form.append('files', file))
  if (sessionId) form.append('session_id', sessionId)
  if (model) form.append('model', model)
  const { data } = await api.post('/api/samples', form)
  return data
}

export async function parseDocument(file) {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post('/api/parse-doc', form)
  return data
}

export async function generateHandwriting(payload) {
  const { data } = await api.post('/api/generate', payload)
  return data
}

export async function getJobStatus(jobId) {
  const { data } = await api.get(`/api/status/${jobId}`)
  return data
}

export async function getJobResult(jobId) {
  const { data } = await api.get(`/api/result/${jobId}`)
  return data
}

export async function exportPdf(jobId, model = null) {
  const { data } = await api.post(
    '/api/export/pdf',
    { job_id: jobId, model },
    { responseType: 'blob' },
  )
  return data
}
