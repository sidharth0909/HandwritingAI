import { useState } from 'react'
import { uploadSamples } from '../api/client'
import useStore from '../store/useStore'
import DrawCanvas from './DrawCanvas'
import UploadZone from './UploadZone'

const MIN = 5
const MAX = 10

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

export default function Step1Samples() {
  const [tab, setTab] = useState('upload')
  const [uploading, setUploading] = useState(false)
  const { sampleFiles, setSamples, setSessionId, setStep, setError } = useStore()

  const addFiles = (incoming) => {
    setSamples([...sampleFiles, ...incoming].slice(0, MAX))
  }

  const removeFile = (index) => {
    setSamples(sampleFiles.filter((_, i) => i !== index))
  }

  const handleUploadSamples = async () => {
    if (sampleFiles.length < MIN) return
    setUploading(true)
    setError(null)
    try {
      const data = await uploadSamples(sampleFiles)
      setSessionId(data.session_id)
      setStep(2)
    } catch (err) {
      const detail = err.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'Failed to upload samples')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="step-panel">
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

      {tab === 'upload' ? (
        <UploadZone
          onFiles={addFiles}
          accept={{ 'image/*': ['.png', '.jpg', '.jpeg', '.webp'] }}
          title="Drop handwriting samples here"
          subtitle="JPG, PNG accepted · 5 to 10 words"
          maxFiles={MAX}
        />
      ) : (
        <DrawCanvas onSave={(file) => addFiles([file])} />
      )}

      <ThumbnailRow files={sampleFiles} onRemove={removeFile} />

      {sampleFiles.length < MIN && (
        <p className="helper-text">Upload at least 5 word samples</p>
      )}
      <p className="body-secondary">
        {sampleFiles.length} of {MAX} samples
      </p>

      <div className="step-actions">
        <button
          type="button"
          className="btn btn-primary"
          disabled={sampleFiles.length < MIN || uploading}
          onClick={handleUploadSamples}
        >
          {uploading ? 'Uploading...' : 'Upload Samples'}
        </button>
      </div>
    </div>
  )
}
