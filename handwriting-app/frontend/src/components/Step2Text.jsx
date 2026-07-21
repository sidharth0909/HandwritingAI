import { useMemo, useState } from 'react'
import { generateHandwriting, parseDocument } from '../api/client'
import useStore, { getModelConfig } from '../store/useStore'
import UploadZone from './UploadZone'

const WORDS_PER_PAGE = 150

function wordCount(text) {
  const t = text.trim()
  return t ? t.split(/\s+/).length : 0
}

/** Step 3 — enter text and start generation with the chosen model. */
export default function Step2Text() {
  const [tab, setTab] = useState('type')
  const [parsing, setParsing] = useState(false)
  const [loading, setLoading] = useState(false)
  const {
    inputText,
    setText,
    pageCount,
    setPageCount,
    setStep,
    setError,
    sessionId,
    selectedModel,
    setJobId,
    updateJobStatus,
  } = useStore()

  const model = getModelConfig(selectedModel)
  const words = useMemo(() => wordCount(inputText), [inputText])
  const estimatedPages = useMemo(
    () => Math.max(1, Math.min(10, Math.ceil(words / WORDS_PER_PAGE) || 1)),
    [words],
  )

  const handleDoc = async (files) => {
    const file = files[0]
    if (!file) return
    setParsing(true)
    setError(null)
    try {
      const data = await parseDocument(file)
      setText(data.text || '')
    } catch (err) {
      const detail = err.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'Failed to parse document')
    } finally {
      setParsing(false)
    }
  }

  const handleGenerate = async () => {
    if (!sessionId) {
      setError('Upload samples before generating.')
      return
    }
    if (!inputText.trim()) return
    setLoading(true)
    setError(null)
    try {
      const { job_id } = await generateHandwriting({
        session_id: sessionId,
        text: inputText.trim(),
        model: selectedModel,
        pages: pageCount,
      })
      setJobId(job_id)
      updateJobStatus({ status: 'pending', message: 'Queued', progress: 0 })
      setStep(4)
    } catch (err) {
      const detail = err.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'Generation failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="step-panel">
      <span className="section-label">Text for {model.name}</span>
      <div className="tabs">
        <button
          type="button"
          className={`tab-btn ${tab === 'type' ? 'tab-btn--active' : ''}`}
          onClick={() => setTab('type')}
        >
          Type text
        </button>
        <button
          type="button"
          className={`tab-btn ${tab === 'doc' ? 'tab-btn--active' : ''}`}
          onClick={() => setTab('doc')}
        >
          Upload document
        </button>
      </div>

      {tab === 'type' ? (
        <>
          <textarea
            className="input-field"
            rows={8}
            placeholder="Paste or type the text you want written in your handwriting..."
            value={inputText}
            onChange={(e) => setText(e.target.value)}
          />
          <p className="body-secondary">
            {words} words — estimated {estimatedPages} page
            {estimatedPages !== 1 ? 's' : ''} at {WORDS_PER_PAGE} words per page
          </p>
        </>
      ) : (
        <>
          <UploadZone
            onFiles={handleDoc}
            accept={{
              'application/pdf': ['.pdf'],
              'application/vnd.openxmlformats-officedocument.wordprocessingml.document': [
                '.docx',
              ],
            }}
            title="Drop document here"
            subtitle="PDF or DOCX"
            multiple={false}
          />
          {parsing && <p className="body-secondary">Parsing document...</p>}
          <textarea
            className="input-field"
            rows={6}
            style={{ marginTop: 12 }}
            value={inputText}
            onChange={(e) => setText(e.target.value)}
          />
        </>
      )}

      <div style={{ marginTop: 20 }}>
        <span className="section-label">Page count</span>
        <div className="page-btns">
          {Array.from({ length: 10 }, (_, i) => i + 1).map((n) => (
            <button
              key={n}
              type="button"
              className={`page-btn ${pageCount === n ? 'page-btn--active' : ''}`}
              onClick={() => setPageCount(n)}
            >
              {n}
            </button>
          ))}
        </div>
      </div>

      <div className="step-actions">
        <button type="button" className="btn" onClick={() => setStep(2)}>
          Back
        </button>
        <button
          type="button"
          className="btn btn-primary"
          disabled={!inputText.trim() || loading}
          onClick={handleGenerate}
        >
          {loading ? 'Starting...' : `Generate with ${model.name}`}
        </button>
      </div>
    </div>
  )
}
