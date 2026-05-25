import { useEffect, useRef } from 'react'
import { fabric } from 'fabric'

export default function DrawCanvas({ onSave }) {
  const canvasRef = useRef(null)
  const fabricRef = useRef(null)

  useEffect(() => {
    if (!canvasRef.current || fabricRef.current) return
    const canvas = new fabric.Canvas(canvasRef.current, {
      isDrawingMode: true,
      backgroundColor: '#ffffff',
      width: 500,
      height: 140,
    })
    canvas.freeDrawingBrush.color = '#1a1a1a'
    canvas.freeDrawingBrush.width = 3
    fabricRef.current = canvas
    return () => {
      canvas.dispose()
      fabricRef.current = null
    }
  }, [])

  const clear = () => {
    const canvas = fabricRef.current
    if (!canvas) return
    canvas.clear()
    canvas.backgroundColor = '#ffffff'
    canvas.renderAll()
  }

  const saveWord = () => {
    const canvas = fabricRef.current
    if (!canvas || !onSave) return
    const dataUrl = canvas.toDataURL({ format: 'png' })
    fetch(dataUrl)
      .then((r) => r.blob())
      .then((blob) => {
        const file = new File([blob], `drawn_${Date.now()}.png`, { type: 'image/png' })
        onSave(file)
        clear()
      })
  }

  return (
    <div>
      <div className="draw-canvas-wrap">
        <canvas ref={canvasRef} />
      </div>
      <div className="btn-row">
        <button type="button" className="btn" onClick={clear}>
          Clear canvas
        </button>
        <button type="button" className="btn" onClick={saveWord}>
          Save word
        </button>
      </div>
    </div>
  )
}
