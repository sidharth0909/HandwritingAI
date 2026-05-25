import { useEffect, useState } from 'react'
import { api, generateHandwriting } from '../api/client'
import useStore, { MODELS } from '../store/useStore'

function ColumnsIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <rect x="2" y="3" width="4" height="14" stroke="currentColor" strokeWidth="1" />
      <rect x="8" y="3" width="4" height="14" stroke="currentColor" strokeWidth="1" />
      <rect x="14" y="3" width="4" height="14" stroke="currentColor" strokeWidth="1" />
    </svg>
  )
}

function ModelBadge({ loaded, weightsExist }) {
  let dotColor = 'var(--color-text-tertiary)'
  let label = 'Weights missing — run download_weights.py'

  if (weightsExist && loaded) {
    dotColor = '#1D9E75'
    label = 'Ready'
  } else if (weightsExist && !loaded) {
    dotColor = '#BA7517'
    label = 'Not loaded'
  }

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        marginTop: 8,
        fontSize: 10,
        fontWeight: 400,
        color: 'var(--color-text-tertiary)',
      }}
    >
      <span
        style={{
          width: 6,
          height: 6,
          borderRadius: '50%',
          background: dotColor,
          flexShrink: 0,
        }}
      />
      {label}
    </span>
  )
}

export default function Step3Models() {
  const [loading, setLoading] = useState(false)
  const [modelStatus, setModelStatus] = useState(null)
  const {
    sessionId,
    inputText,
    pageCount,
    selectedModel,
    setModel,
    setJobId,
    setStep,
    setError,
    updateJobStatus,
  } = useStore()

  const isCompare = selectedModel === 'compare'

  useEffect(() => {
    api
      .get('/api/model-status')
      .then((res) => setModelStatus(res.data))
      .catch(() => setModelStatus(null))
  }, [])

  const handleGenerate = async () => {
    if (!sessionId) {
      setError('Upload samples before generating.')
      return
    }
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
      <span className="section-label">Single model</span>
      <div className="model-grid">
        {MODELS.map((m) => {
          const status = modelStatus?.[m.id]
          return (
            <button
              key={m.id}
              type="button"
              className={`model-card ${!isCompare && selectedModel === m.id ? 'model-card--selected' : ''}`}
              onClick={() => setModel(m.id)}
            >
              <span className="model-tag">{m.tag}</span>
              <span className="model-name">{m.name}</span>
              <span className="body-secondary">{m.description}</span>
              {status && (
                <ModelBadge
                  loaded={status.loaded}
                  weightsExist={status.weights_exist}
                />
              )}
            </button>
          )
        })}
      </div>

      <span className="section-label" style={{ marginTop: 20 }}>
        Or compare all
      </span>
      <button
        type="button"
        className={`compare-card ${isCompare ? 'compare-card--selected' : ''}`}
        onClick={() => setModel('compare')}
      >
        <ColumnsIcon />
        <span>
          <span className="model-name">Run all three side by side</span>
          <span className="body-secondary block-mt">
            Pick the best result after generation
          </span>
        </span>
      </button>

      <div className="step-actions">
        <button
          type="button"
          className="btn btn-primary"
          disabled={loading}
          onClick={handleGenerate}
        >
          {loading ? 'Starting...' : 'Generate'}
        </button>
      </div>
    </div>
  )
}
