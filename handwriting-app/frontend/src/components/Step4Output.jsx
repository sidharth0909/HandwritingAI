import { useEffect, useRef } from 'react'
import {
  exportPdf,
  fileUrl,
  getJobResult,
  getJobStatus,
} from '../api/client'
import useStore, { MODELS } from '../store/useStore'
import PagePreview from './PagePreview'

const POLL_MS = 2000

const PROGRESS_STEPS = [
  'Style extracted',
  'Text split into words',
  'Generating words',
  'Assembling pages',
  'Preparing export',
]

function stepDotState(index, progress) {
  const thresholds = [15, 30, 50, 75, 95]
  const t = thresholds[index]
  if (progress >= t + 5) return 'done'
  if (progress >= (thresholds[index - 1] ?? 0)) return 'active'
  return 'pending'
}

function downloadBlob(blob, name) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = name
  a.click()
  URL.revokeObjectURL(url)
}

export default function Step4Output() {
  const store = useStore()
  const pollRef = useRef(null)

  const {
    jobId,
    jobStatus,
    jobMessage,
    jobProgress,
    selectedModel,
    results,
    compareResults,
    activeCompareModel,
    previewPage,
    updateJobStatus,
    setResults,
    setActiveCompareModel,
    setPreviewPage,
    setStep,
    resetAll,
    setError,
  } = store

  const isCompare = selectedModel === 'compare'
  const loading = jobStatus === 'pending' || jobStatus === 'processing'

  useEffect(() => {
    if (!jobId || jobStatus === 'done' || jobStatus === 'error') return

    const poll = async () => {
      try {
        const status = await getJobStatus(jobId)
        updateJobStatus(status)
        if (status.status === 'done') {
          const result = await getJobResult(jobId)
          if (result.is_compare) {
            setResults(null, result.compare)
            if (!activeCompareModel) {
              setActiveCompareModel('diffusionpen')
            }
          } else {
            setResults(result.pages, null)
          }
          clearInterval(pollRef.current)
        } else if (status.status === 'error') {
          setError(status.message || 'Generation failed')
          clearInterval(pollRef.current)
        }
      } catch (err) {
        const detail = err.response?.data?.detail
        setError(typeof detail === 'string' ? detail : 'Status check failed')
        clearInterval(pollRef.current)
      }
    }

    poll()
    pollRef.current = setInterval(poll, POLL_MS)
    return () => clearInterval(pollRef.current)
  }, [jobId, jobStatus])

  const activePages = () => {
    if (isCompare && compareResults) {
      const key = activeCompareModel || 'diffusionpen'
      return compareResults[key] || []
    }
    return results || []
  }

  const pages = activePages()
  const pageIndex = Math.min(previewPage, Math.max(0, pages.length - 1))
  const currentSrc = pages[pageIndex]

  const handlePng = async () => {
    if (!currentSrc) return
    const res = await fetch(fileUrl(currentSrc))
    const blob = await res.blob()
    downloadBlob(blob, `page_${pageIndex + 1}.png`)
  }

  const handlePdf = async () => {
    try {
      const model = isCompare ? activeCompareModel : selectedModel
      const blob = await exportPdf(jobId, isCompare ? model : null)
      downloadBlob(blob, 'handwriting.pdf')
    } catch (err) {
      const detail = err.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'PDF export failed')
    }
  }

  if (loading) {
    return (
      <div className="step-panel output-loading">
        <div className="spinner-lg" role="status" />
        <p className="output-status">{jobMessage || 'Processing...'}</p>
        <ul className="progress-list">
          {PROGRESS_STEPS.map((label, i) => (
            <li key={label} className={`progress-item progress-item--${stepDotState(i, jobProgress)}`}>
              <span className="progress-dot" />
              <span>{label}</span>
            </li>
          ))}
        </ul>
      </div>
    )
  }

  if (jobStatus === 'done' && isCompare && compareResults) {
    const maxComparePages = Math.max(
      1,
      ...MODELS.map((m) => (compareResults[m.id] || []).length),
    )
    const cmpIndex = Math.min(pageIndex, maxComparePages - 1)

    return (
      <div className="step-panel">
        <div className="compare-grid">
          {MODELS.map((m) => {
            const modelPages = compareResults[m.id] || []
            const src = modelPages[cmpIndex] || modelPages[0]
            const selected = activeCompareModel === m.id
            return (
              <div key={m.id} className="compare-col">
                <span className="section-label">
                  {m.name} · {m.tag}
                </span>
                <PagePreview
                  src={src}
                  alt={`${m.name} preview`}
                  selected={selected}
                  onSelect={() => setActiveCompareModel(m.id)}
                />
                <button
                  type="button"
                  className={`btn ${selected ? 'btn-primary' : ''}`}
                  onClick={() => setActiveCompareModel(m.id)}
                >
                  Use this result
                </button>
              </div>
            )
          })}
        </div>
        {maxComparePages > 1 && (
          <PageNav
            page={cmpIndex}
            total={maxComparePages}
            onPrev={() => setPreviewPage(Math.max(0, cmpIndex - 1))}
            onNext={() => setPreviewPage(Math.min(maxComparePages - 1, cmpIndex + 1))}
          />
        )}
        {activeCompareModel && (
          <DownloadRow onPng={handlePng} onPdf={handlePdf} />
        )}
        <Step4Footer onBack={() => setStep(3)} onReset={resetAll} />
      </div>
    )
  }

  if (jobStatus === 'done' && results) {
    const modelLabel = MODELS.find((m) => m.id === selectedModel)?.name || selectedModel
    return (
      <div className="step-panel">
        <div className="single-result">
          <PagePreview src={currentSrc} alt="Generated page" />
          {pages.length > 1 && (
            <PageNav
              page={pageIndex}
              total={pages.length}
              onPrev={() => setPreviewPage(Math.max(0, pageIndex - 1))}
              onNext={() => setPreviewPage(Math.min(pages.length - 1, pageIndex + 1))}
            />
          )}
          <p className="body-secondary center">
            {modelLabel} · {pages.length} page{pages.length !== 1 ? 's' : ''}
          </p>
        </div>
        <DownloadRow onPng={handlePng} onPdf={handlePdf} />
        <Step4Footer onBack={() => setStep(3)} onReset={resetAll} />
      </div>
    )
  }

  return (
    <div className="step-panel">
      <p className="body-secondary">Start generation from step 3 to see output here.</p>
      <Step4Footer onBack={() => setStep(3)} onReset={resetAll} />
    </div>
  )
}

function PageNav({ page, total, onPrev, onNext }) {
  return (
    <div className="page-nav">
      <button type="button" className="nav-arrow" disabled={page <= 0} onClick={onPrev}>
        ‹
      </button>
      <span className="body-secondary">
        Page {page + 1} of {total}
      </span>
      <button type="button" className="nav-arrow" disabled={page >= total - 1} onClick={onNext}>
        ›
      </button>
    </div>
  )
}

function DownloadRow({ onPng, onPdf }) {
  return (
    <div className="download-row">
      <button type="button" className="btn" onClick={onPng}>
        Download PNG
      </button>
      <button type="button" className="btn" onClick={onPdf}>
        Download PDF
      </button>
    </div>
  )
}

function Step4Footer({ onBack, onReset }) {
  return (
    <div className="step4-footer">
      <span className="body-secondary">Step 4 of 4</span>
      <div className="btn-row">
        <button type="button" className="btn" onClick={onBack}>
          Back
        </button>
        <button type="button" className="btn" onClick={onReset}>
          New generation
        </button>
      </div>
    </div>
  )
}
