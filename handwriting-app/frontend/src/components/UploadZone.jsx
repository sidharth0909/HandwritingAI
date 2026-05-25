import { useDropzone } from 'react-dropzone'

function UploadIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M12 16V6M12 6L8 10M12 6L16 10"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M4 18h16"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
    </svg>
  )
}

export default function UploadZone({
  onFiles,
  accept,
  title,
  subtitle,
  maxFiles,
  multiple = true,
}) {
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: (accepted) => onFiles(accepted),
    accept,
    maxFiles: maxFiles ?? (multiple ? undefined : 1),
    multiple,
  })

  return (
    <div
      {...getRootProps()}
      className={`upload-zone ${isDragActive ? 'upload-zone--active' : ''}`}
    >
      <input {...getInputProps()} />
      <UploadIcon />
      <p className="upload-zone-title">{title}</p>
      {subtitle && <p className="upload-zone-sub">{subtitle}</p>}
    </div>
  )
}
