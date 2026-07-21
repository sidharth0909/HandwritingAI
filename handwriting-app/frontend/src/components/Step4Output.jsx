import { useEffect, useMemo, useRef } from 'react'
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
  if (progress >= thresholds[index] + 5) return 'done'
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

function SampleThumbs({ files }) {
  const urls = useMemo(
    () => files.map((file) => URL.createObjectURL(file)),
    [files],
  )

  useEffect(() => {
    return () => {
      urls.forEach((u) => URL.revokeObjectURL(u))
    }
  }, [urls])

  if (!files.length) {
    return <p className="helper-text">No samples in this session.</p>
  }

  return (
    <div className="samples-thumbs samples-thumbs--row">
      {urls.map((src, i) => (
        <img
          key={`${files[i].name}-${i}`}
          src={src}
          alt={`Sample ${i + 1}`}
          className="sample-thumb"
        />
      ))}
    </div>
  )
}

function StyleSourceBadge({ source }) {
  const map = {
    user: { className: 'style-badge style-badge--user', label: 'Your style' },
    fallback: {
      className: 'style-badge style-badge--fallback',
      label: 'Built-in sample style',
    },
    mixed: { className: 'style-badge style-badge--mixed', label: 'Mixed styles' },
    mock: { className: 'style-badge style-badge--fallback', label: 'Mock output' },
    error: { className: 'style-badge style-badge--fallback', label: 'Error fallback' },
  }
  const info = map[source] || {
    className: 'style-badge',
    label: source || 'Unknown',
  }
  return <span className={info.className}>{info.label}</span>
}

function RunSummary({ sampleFiles, inputText, meta, modelLabel }) {
  const source = meta?.style_source || 'user'
  const styleLabel =
    meta?.style_source_label ||
    (source === 'user'
      ? 'Your uploaded handwriting style'
      : 'Built-in / fallback style')
  const words = meta?.words || (inputText || '').trim().split(/\s+/).filter(Boolean)
  const wordSources = meta?.word_sources || []

  return (
    <div className="run-summary">
      <div className="run-summary-block">
        <span className="section-label">Your samples</span>
        <SampleThumbs files={sampleFiles} />
      </div>

      <div className="run-summary-block">
        <span className="section-label">Input text</span>
        <p className="run-summary-text">
          {inputText?.trim() || meta?.input_text || '—'}
        </p>
        {words.length > 0 && (
          <p className="helper-text">
            {words.length} word{words.length !== 1 ? 's' : ''}
            {modelLabel ? ` · ${modelLabel}` : ''}
          </p>
        )}
      </div>

      <div className="run-summary-block">
        <span className="section-label">Style used</span>
        <div className="style-used-row">
          <StyleSourceBadge source={source} />
          <p className="body-secondary" style={{ margin: 0 }}>
            {styleLabel}
          </p>
        </div>
        {meta?.style_text && (
          <p className="helper-text">
            Style crop transcription: “{meta.style_text}”
          </p>
        )}
        {meta?.style_crop_url && (
          <div className="style-crop-wrap">
            <img
              src={fileUrl(meta.style_crop_url)}
              alt="Style crop used for generation"
              className="style-crop-img"
            />
            <span className="helper-text">Crop actually fed to the model</span>
          </div>
        )}
        {wordSources.length > 0 && words.length === wordSources.length && (
          <ul className="word-source-list">
            {words.map((w, i) => (
              <li key={`${w}-${i}`}>
                <code>{w}</code>
                <span
                  className={
                    wordSources[i] === 'user'
                      ? 'word-src word-src--user'
                      : 'word-src word-src--fallback'
                  }
                >
                  {wordSources[i] === 'user' ? 'your style' : 'built-in style'}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

export default function Step4Output() {
  const pollRef = useRef(null)

  const {
    jobId,
    jobStatus,
    jobMessage,
    jobProgress,
    selectedModel,
    sampleFiles,
    inputText,
    results,
    compareResults,
    resultMeta,
    activeCompareModel,
    previewPage,
    updateJobStatus,
    setResults,
    setActiveCompareModel,
    setPreviewPage,
    setStep,
    resetAll,
    setError,
  } = useStore()

  const isCompare = selectedModel === 'compare'
  const loading = jobStatus === 'pending' || jobStatus === 'processing'
  const modelLabel = MODELS.find((m) => m.id === selectedModel)?.name || selectedModel

  useEffect(() => {
    if (!jobId || jobStatus === 'done' || jobStatus === 'error') return

    const poll = async () => {
      try {
        const status = await getJobStatus(jobId)
        updateJobStatus(status)
        if (status.status === 'done') {
          const result = await getJobResult(jobId)
          if (result.is_compare) {
            setResults(null, result.compare, result.meta || null)
            if (!activeCompareModel) {
              setActiveCompareModel('diffusionpen')
            }
          } else {
            setResults(result.pages, null, result.meta || null)
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
            <li
              key={label}
              className={`progress-item progress-item--${stepDotState(i, jobProgress)}`}
            >
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
        <div className="output-layout">
          <aside className="output-layout__side">
            <RunSummary
              sampleFiles={sampleFiles}
              inputText={inputText}
              meta={resultMeta}
              modelLabel="Compare"
            />
          </aside>
          <div className="output-layout__main">
            <span className="section-label">Generated output</span>
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
                onNext={() =>
                  setPreviewPage(Math.min(maxComparePages - 1, cmpIndex + 1))
                }
              />
            )}
            {activeCompareModel && (
              <DownloadRow onPng={handlePng} onPdf={handlePdf} />
            )}
          </div>
        </div>
        <Step4Footer onBack={() => setStep(3)} onReset={resetAll} />
      </div>
    )
  }

  if (jobStatus === 'done' && results) {
    return (
      <div className="step-panel">
        <div className="output-layout">
          <aside className="output-layout__side">
            <RunSummary
              sampleFiles={sampleFiles}
              inputText={inputText}
              meta={resultMeta}
              modelLabel={modelLabel}
            />
          </aside>
          <div className="output-layout__main">
            <span className="section-label">Generated output</span>
            <div className="single-result">
              <PagePreview src={currentSrc} alt="Generated page" />
              {pages.length > 1 && (
                <PageNav
                  page={pageIndex}
                  total={pages.length}
                  onPrev={() => setPreviewPage(Math.max(0, pageIndex - 1))}
                  onNext={() =>
                    setPreviewPage(Math.min(pages.length - 1, pageIndex + 1))
                  }
                />
              )}
              <p className="body-secondary center">
                {modelLabel} · {pages.length} page{pages.length !== 1 ? 's' : ''}
              </p>
            </div>
            <DownloadRow onPng={handlePng} onPdf={handlePdf} />
          </div>
        </div>
        <Step4Footer onBack={() => setStep(3)} onReset={resetAll} />
      </div>
    )
  }

  return (
    <div className="step-panel">
      <p className="body-secondary">
        Enter text and generate from step 3 to see output here.
      </p>
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
      <button
        type="button"
        className="nav-arrow"
        disabled={page >= total - 1}
        onClick={onNext}
      >
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
