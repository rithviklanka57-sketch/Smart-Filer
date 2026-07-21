import { FileText, CheckCircle, Clock, AlertCircle, ExternalLink, FolderOpen, Sparkles } from 'lucide-react'

export interface DocumentData {
  id: string
  filename: string
  status: string
  doc_type?: string
  summary?: string
  error_message?: string
  placement?: {
    mode: 'auto' | 'question' | 'fallback'
    candidates: Array<{ folder_id: string; folder_name: string; path: string; confidence: number }>
    question?: string
    options?: string[]
    why?: string
  }
  drive_link?: string
}

interface Props {
  doc: DocumentData
  onAnswer?: (folderId: string, folderName: string) => void
  onConfirm?: (folderId: string, folderName: string) => void
}

export default function DocumentCard({ doc, onAnswer, onConfirm }: Props) {
  const statusInfo = {
    pending: doc.placement
      ? { label: 'Ready to file', color: 'var(--color-brand-400)', icon: <CheckCircle size={13} /> }
      : { label: 'Processing', color: 'var(--color-warning)', icon: <Clock size={13} className="status-pulse" /> },
    extracting: { label: 'Extracting text', color: 'var(--color-info)', icon: <Clock size={13} className="status-pulse" /> },
    classifying: { label: 'Analyzing with AI', color: 'var(--color-brand-400)', icon: <Clock size={13} className="status-pulse" /> },
    needs_input: { label: 'Needs your input', color: 'var(--color-warning)', icon: <AlertCircle size={13} /> },
    placing: { label: 'Uploading to Drive', color: 'var(--color-info)', icon: <Clock size={13} className="status-pulse" /> },
    placed: { label: 'Filed in Drive', color: 'var(--color-success)', icon: <CheckCircle size={13} /> },
    error: { label: 'Error', color: 'var(--color-error)', icon: <AlertCircle size={13} /> },
  }[doc.status] ?? { label: doc.status, color: 'var(--color-text-muted)', icon: <Clock size={13} /> }

  const placement = doc.placement
  const best = placement?.candidates?.[0]
  const confidence = best?.confidence ?? 0

  const badgeClass = confidence >= 0.85 ? 'badge-high' : confidence >= 0.6 ? 'badge-medium' : 'badge-low'

  return (
    <div id={`doc-card-${doc.id}`} className="glass-card fade-in-up" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.875rem' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
        <div style={{
          width: 38, height: 38, borderRadius: 10,
          background: 'var(--color-surface-3)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
        }}>
          <FileText size={18} color="var(--color-brand-400)" />
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 600, fontSize: '0.9rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {doc.filename}
          </div>
          {doc.doc_type && (
            <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: 2, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              {doc.doc_type}
            </div>
          )}
        </div>
        {/* Status badge */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', fontSize: '0.75rem', color: statusInfo.color, flexShrink: 0 }}>
          {statusInfo.icon}
          {statusInfo.label}
        </div>
      </div>

      {/* Summary */}
      {doc.summary && (
        <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>
          {doc.summary}
        </p>
      )}

      {/* Placement suggestion */}
      {placement && (
        <div style={{
          background: 'var(--color-surface-3)',
          border: '1px solid var(--color-border)',
          borderRadius: 10,
          padding: '0.875rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.625rem',
        }}>
          {best && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <FolderOpen size={14} color="var(--color-brand-400)" />
              <span style={{ fontSize: '0.8rem', fontWeight: 600 }}>{best.path}</span>
              <span className={`badge ${badgeClass}`} style={{ marginLeft: 'auto' }}>
                {Math.round(confidence * 100)}%
              </span>
            </div>
          )}

          {placement.why && (
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.4rem' }}>
              <Sparkles size={12} color="var(--color-text-muted)" style={{ flexShrink: 0, marginTop: 2 }} />
              <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', lineHeight: 1.5 }}>
                {placement.why}
              </span>
            </div>
          )}

          {/* Folder choices when input is needed */}
          {(placement.mode === 'question' || placement.mode === 'fallback' || doc.status === 'needs_input') && placement.candidates && placement.candidates.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', paddingTop: '0.25rem', borderTop: '1px solid var(--color-border)' }}>
              <p style={{ margin: 0, fontSize: '0.8rem', fontWeight: 500 }}>
                {placement.question || 'Select target folder:'}
              </p>
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                {placement.candidates.slice(0, 3).map(c => (
                  <button
                    id={`answer-btn-${c.folder_id}`}
                    key={c.folder_id}
                    className="btn-secondary"
                    style={{ fontSize: '0.75rem', padding: '0.45rem 0.8rem', cursor: 'pointer' }}
                    onClick={() => onAnswer ? onAnswer(c.folder_id, c.folder_name) : onConfirm?.(c.folder_id, c.folder_name)}
                  >
                    📁 {c.path} ({Math.round(c.confidence * 100)}%)
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Confirm button */}
          {(placement.mode === 'auto' || doc.status === 'pending') && doc.status !== 'placed' && best && (
            <button
              id={`confirm-btn-${doc.id}`}
              className="btn-primary"
              style={{ alignSelf: 'flex-start', fontSize: '0.8rem', padding: '0.5rem 1rem', marginTop: '0.25rem' }}
              onClick={() => onConfirm?.(best.folder_id, best.folder_name)}
            >
              <CheckCircle size={14} /> File in {best.folder_name}
            </button>
          )}
        </div>
      )}
      {/* Fallback when needs_input but no placement or candidates found */}
      {doc.status === 'needs_input' && (!placement || !placement.candidates || placement.candidates.length === 0) && (
        <div style={{
          background: 'var(--color-surface-3)',
          border: '1px solid var(--color-border)',
          borderRadius: 10,
          padding: '0.875rem',
          fontSize: '0.8rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.5rem',
        }}>
          <p style={{ margin: 0, color: 'var(--color-text-secondary)' }}>
            No cached Drive folders found to suggest placement. Please sync your Google Drive folder tree.
          </p>
          <a href="/settings" className="btn-secondary" style={{ alignSelf: 'flex-start', fontSize: '0.75rem', padding: '0.4rem 0.75rem', textDecoration: 'none' }}>
            ⚙️ Go to Settings & Sync Folders
          </a>
        </div>
      )}

      {/* Placed — Drive link */}
      {doc.status === 'placed' && doc.drive_link && (
        <a href={doc.drive_link} target="_blank" rel="noreferrer"
          style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.8rem', color: 'var(--color-brand-400)', textDecoration: 'none' }}>
          <ExternalLink size={13} /> Open in Google Drive
        </a>
      )}

      {/* Error */}
      {doc.status === 'error' && doc.error_message && (
        <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--color-error)' }}>
          {doc.error_message}
        </p>
      )}
    </div>
  )
}
