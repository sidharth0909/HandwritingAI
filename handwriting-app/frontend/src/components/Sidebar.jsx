import useStore, { MODELS } from '../store/useStore'

const STEPS = [
  { id: 1, label: 'Model', subtitle: 'Choose generator' },
  { id: 2, label: 'Samples', subtitle: 'Style reference images' },
  { id: 3, label: 'Text', subtitle: 'Content and pages' },
  { id: 4, label: 'Output', subtitle: 'Preview and export' },
]

function CheckIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
      <path
        d="M2.5 6L5 8.5L9.5 3.5"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function stepStatus(stepId, currentStep, store) {
  const done =
    (stepId === 1 && currentStep > 1) ||
    (stepId === 2 && store.sessionId) ||
    (stepId === 3 && store.jobId) ||
    (stepId === 4 && store.jobStatus === 'done')
  if (stepId === currentStep) return 'active'
  if (done) return 'done'
  if (stepId < currentStep) return 'done'
  return 'pending'
}

function dynamicSubtitle(stepId, store) {
  if (stepId === 1) {
    const m = MODELS.find((x) => x.id === store.selectedModel)
    return m ? m.name : STEPS[0].subtitle
  }
  if (stepId === 2) {
    const n = store.sampleFiles.length
    if (store.sessionId) return 'Samples uploaded'
    if (n) return `${n} word${n !== 1 ? 's' : ''} added`
    return STEPS[1].subtitle
  }
  if (stepId === 3) {
    const words = store.inputText.trim().split(/\s+/).filter(Boolean).length
    if (words) return `${words} words, ${store.pageCount} page(s)`
    return STEPS[2].subtitle
  }
  if (stepId === 4) {
    if (store.jobStatus === 'done') return 'Ready to download'
    if (store.jobStatus) return store.jobMessage || 'Generating'
    return STEPS[3].subtitle
  }
  return STEPS[stepId - 1].subtitle
}

export default function Sidebar() {
  const store = useStore()
  const { currentStep, setStep } = store

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <span className="logo-text">
          Handwriting<span className="logo-ai">AI</span>
        </span>
      </div>
      <nav className="step-nav">
        {STEPS.map((step) => {
          const status = stepStatus(step.id, currentStep, store)
          const isActive = status === 'active'
          const isDone = status === 'done'
          return (
            <button
              key={step.id}
              type="button"
              className={`step-nav-item ${isActive ? 'step-nav-item--active' : ''}`}
              onClick={() => setStep(step.id)}
            >
              <span
                className={`step-circle ${
                  isActive ? 'step-circle--active' : isDone ? 'step-circle--done' : ''
                }`}
              >
                {isDone && !isActive ? <CheckIcon /> : step.id}
              </span>
              <span>
                <span className="step-nav-label">{step.label}</span>
                <span className="step-nav-sub">{dynamicSubtitle(step.id, store)}</span>
              </span>
            </button>
          )
        })}
      </nav>
    </aside>
  )
}
