import Sidebar from './components/Sidebar'
import Step1Samples from './components/Step1Samples'
import Step2Text from './components/Step2Text'
import Step3Models from './components/Step3Models'
import Step4Output from './components/Step4Output'
import useStore from './store/useStore'

function StepRouter() {
  const step = useStore((s) => s.currentStep)
  switch (step) {
    case 1:
      return <Step3Models />
    case 2:
      return <Step1Samples />
    case 3:
      return <Step2Text />
    case 4:
      return <Step4Output />
    default:
      return <Step3Models />
  }
}

export default function App() {
  const error = useStore((s) => s.error)
  const setError = useStore((s) => s.setError)

  return (
    <div className="app-shell">
      <Sidebar />
      <main className="main-area">
        <div className="main-container">
          {error && (
            <div className="alert-error" role="alert">
              <span>{error}</span>
              <button type="button" className="btn btn-destructive" onClick={() => setError(null)}>
                Dismiss
              </button>
            </div>
          )}
          <StepRouter />
        </div>
      </main>
    </div>
  )
}
