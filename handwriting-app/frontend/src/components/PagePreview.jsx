import { fileUrl } from '../api/client'

export default function PagePreview({ src, alt, selected, onSelect, label }) {
  return (
    <button
      type="button"
      className={`page-preview ${selected ? 'page-preview--selected' : ''}`}
      onClick={onSelect}
      disabled={!onSelect}
    >
      {selected && <span className="page-preview-badge">Selected</span>}
      {label && <span className="section-label">{label}</span>}
      <img src={fileUrl(src)} alt={alt} className="page-preview-img" />
    </button>
  )
}
