import { useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, CloudUpload } from 'lucide-react'

interface Props {
  onFiles: (files: File[]) => void
  disabled?: boolean
}

export default function UploadDropzone({ onFiles, disabled }: Props) {
  const onDrop = useCallback((accepted: File[]) => {
    if (accepted.length > 0) onFiles(accepted)
  }, [onFiles])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    disabled,
    accept: {
      'application/pdf': ['.pdf'],
      'image/*': ['.png', '.jpg', '.jpeg', '.tiff', '.bmp'],
      'text/plain': ['.txt', '.md'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    },
    multiple: true,
  })

  return (
    <div
      id="upload-dropzone"
      {...getRootProps()}
      style={{
        border: `2px dashed ${isDragActive ? 'var(--color-brand-400)' : 'var(--color-border)'}`,
        borderRadius: 16,
        padding: '3rem 2rem',
        textAlign: 'center',
        cursor: disabled ? 'not-allowed' : 'pointer',
        background: isDragActive
          ? 'rgba(77, 120, 255, 0.06)'
          : 'rgba(30, 37, 53, 0.4)',
        transition: 'all 0.2s ease',
        opacity: disabled ? 0.5 : 1,
      }}
    >
      <input id="upload-file-input" {...getInputProps()} />
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.75rem' }}>
        <div style={{
          width: 56, height: 56,
          borderRadius: '50%',
          background: isDragActive
            ? 'rgba(77, 120, 255, 0.2)'
            : 'var(--color-surface-3)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          transition: 'all 0.2s',
        }}>
          {isDragActive
            ? <CloudUpload size={26} color="var(--color-brand-400)" />
            : <Upload size={26} color="var(--color-text-secondary)" />
          }
        </div>
        <div>
          <p style={{ margin: 0, fontWeight: 600, color: isDragActive ? 'var(--color-brand-400)' : 'var(--color-text-primary)' }}>
            {isDragActive ? 'Drop files here' : 'Drag & drop files here'}
          </p>
          <p style={{ margin: '0.35rem 0 0', fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
            or click to browse — PDF, DOCX, images, text
          </p>
        </div>
      </div>
    </div>
  )
}
