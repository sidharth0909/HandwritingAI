import { useEffect, useState } from 'react'
import { api } from '../api/client'
import useStore, { MODELS } from '../store/useStore'

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

/** Step 1 — choose a single model before collecting samples. */
export default function Step3Models() {
  const [modelStatus, setModelStatus] = useState(null)
  const { selectedModel, setModel, setStep } = useStore()

  useEffect(() => {
    api
      .get('/api/model-status')
      .then((res) => setModelStatus(res.data))
      .catch(() => setModelStatus(null))
  }, [])

  const selected = MODELS.find((m) => m.id === selectedModel) || MODELS[0]

  return (
    <div className="step-panel">
      <span className="section-label">Choose a model</span>
      <p className="body-secondary" style={{ marginBottom: 16 }}>
        Sample requirements depend on the model you pick.
      </p>
      <div className="model-grid">
        {MODELS.map((m) => {
          const status = modelStatus?.[m.id]
          return (
            <button
              key={m.id}
              type="button"
              className={`model-card ${selectedModel === m.id ? 'model-card--selected' : ''}`}
              onClick={() => setModel(m.id)}
            >
              <span className="model-tag">{m.tag}</span>
              <span className="model-name">{m.name}</span>
              <span className="body-secondary">{m.description}</span>
              <span className="body-secondary" style={{ display: 'block', marginTop: 8, fontSize: 12 }}>
                {m.sampleHint}
              </span>
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

      <div className="step-actions">
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => setStep(2)}
        >
          Continue with {selected.name}
        </button>
      </div>
    </div>
  )
}
