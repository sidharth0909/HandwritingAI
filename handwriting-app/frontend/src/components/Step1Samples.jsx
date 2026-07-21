import { useEffect, useState } from 'react'
import { uploadSamples } from '../api/client'
import useStore, { getModelConfig } from '../store/useStore'
import DrawCanvas from './DrawCanvas'
import UploadZone from './UploadZone'

function ThumbnailRow({ files, onRemove }) {
  if (!files.length) return null
  return (
    <div className="thumb-row">
      {files.map((file, i) => (
        <div key={`${file.name}-${i}`} className="thumb-item">
          <img
            src={URL.createObjectURL(file)}
            alt={file.name}
            className="thumb-img"
          />
          <span className="thumb-name">{file.name}</span>
          {onRemove && (
            <button
              type="button"
              className="thumb-remove"
              onClick={() => onRemove(i)}
              aria-label="Remove"
            >
              x
            </button>
          )}
        </div>
      ))}
    </div>
  )
}

/** Step 2 — collect samples shaped for the selected model. */
export default function Step1Samples() {
  const [tab, setTab] = useState('upload')
  const [uploading, setUploading] = useState(false)
  const {
    sampleFiles,
    setSamples,
    setSessionId,
    setStep,
    setError,
    selectedModel,
  } = useStore()

  const config = getModelConfig(selectedModel)
  const minSamples = config.minSamples
  const maxSamples = config.maxSamples
  const allowDraw = config.sampleMode === 'flexible'

  useEffect(() => {
    if (!allowDraw && tab === 'draw') setTab('upload')
  }, [allowDraw, tab])

  const addFiles = (incoming) => {
    setSamples([...sampleFiles, ...incoming].slice(0, maxSamples))
  }

  const removeFile = (index) => {
    setSamples(sampleFiles.filter((_, i) => i !== index))
  }

  const handleUploadSamples = async () => {
    if (sampleFiles.length < minSamples) return
    setUploading(true)
    setError(null)
    try {
      const data = await uploadSamples(sampleFiles, null, selectedModel)
      setSessionId(data.session_id)
      setStep(3)
    } catch (err) {
      const detail = err.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'Failed to upload samples')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="step-panel">
      <span className="section-label">
        Samples for {config.name}
      </span>
      <p className="body-secondary" style={{ marginBottom: 16 }}>
        {config.sampleHint}
      </p>

      {allowDraw ? (
        <div className="tabs">
          <button
            type="button"
            className={`tab-btn ${tab === 'upload' ? 'tab-btn--active' : ''}`}
            onClick={() => setTab('upload')}
          >
            Upload
          </button>
          <button
            type="button"
            className={`tab-btn ${tab === 'draw' ? 'tab-btn--active' : ''}`}
            onClick={() => setTab('draw')}
          >
            Draw
          </button>
        </div>
      ) : (
        <p className="helper-text" style={{ marginBottom: 12 }}>
          Zero-shot: one clear photo is enough — a full page is fine; we auto-crop a word.
        </p>
      )}

      {tab === 'upload' || !allowDraw ? (
        <UploadZone
          onFiles={addFiles}
          accept={{ 'image/*': ['.png', '.jpg', '.jpeg', '.webp'] }}
          title={
            allowDraw
              ? 'Drop handwriting samples here'
              : 'Drop pen-and-paper photos here'
          }
          subtitle={
            allowDraw
              ? `JPG, PNG accepted · ${minSamples} to ${maxSamples} words`
              : `Clear photos · ${minSamples}${maxSamples > minSamples ? ` to ${maxSamples}` : ''} single-word image${minSamples === 1 && maxSamples === 1 ? '' : 's'}`
          }
          maxFiles={maxSamples}
        />
      ) : (
        <DrawCanvas onSave={(file) => addFiles([file])} />
      )}

      <ThumbnailRow files={sampleFiles} onRemove={removeFile} />

      {sampleFiles.length < minSamples && (
        <p className="helper-text">
          Add at least {minSamples} word sample{minSamples !== 1 ? 's' : ''}
        </p>
      )}
      <p className="body-secondary">
        {sampleFiles.length} of {maxSamples} samples
      </p>

      <div className="step-actions">
        <button type="button" className="btn" onClick={() => setStep(1)}>
          Back
        </button>
        <button
          type="button"
          className="btn btn-primary"
          disabled={sampleFiles.length < minSamples || uploading}
          onClick={handleUploadSamples}
        >
          {uploading ? 'Uploading...' : 'Continue'}
        </button>
      </div>
    </div>
  )
}
