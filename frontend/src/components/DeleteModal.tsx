import { useState } from 'react'
import { AlertTriangle, Trash2, X } from 'lucide-react'
import type { DocumentData } from './DocumentCard'

interface Props {
  isOpen: boolean
  documents: DocumentData[]
  onClose: () => void
  onConfirm: (deleteFromDrive: boolean) => Promise<void>
  loading?: boolean
}

export default function DeleteModal({ isOpen, documents, onClose, onConfirm, loading }: Props) {
  const [deleteFromDrive, setDeleteFromDrive] = useState(true)

  if (!isOpen || documents.length === 0) return null

  const hasPlacedFiles = documents.some(d => d.status === 'placed' || Boolean(d.drive_link))

  const handleConfirm = async () => {
    await onConfirm(hasPlacedFiles ? deleteFromDrive : false)
  }

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 9999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'rgba(0, 0, 0, 0.7)',
        backdropFilter: 'blur(6px)',
        WebkitBackdropFilter: 'blur(6px)',
        padding: '1rem',
      }}
      onClick={onClose}
    >
      <div
        className="glass-card fade-in-up"
        style={{
          width: '100%',
          maxWidth: 480,
          background: 'var(--color-surface-2)',
          border: '1px solid var(--color-border)',
          borderRadius: 16,
          padding: '1.5rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '1.25rem',
          boxShadow: '0 20px 40px rgba(0,0,0,0.5)',
        }}
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{
            width: 42, height: 42, borderRadius: 12,
            background: 'rgba(244, 63, 94, 0.15)',
            border: '1px solid rgba(244, 63, 94, 0.3)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: 'var(--color-error)', flexShrink: 0,
          }}>
            <AlertTriangle size={22} />
          </div>
          <div>
            <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700 }}>
              {documents.length === 1 ? 'Delete Document' : `Delete ${documents.length} Documents`}
            </h3>
            <p style={{ margin: '0.2rem 0 0', fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
              Confirm deletion from Smart Filer
            </p>
          </div>
          <button
            onClick={onClose}
            style={{
              marginLeft: 'auto', background: 'none', border: 'none',
              color: 'var(--color-text-muted)', cursor: 'pointer', padding: 4,
            }}
          >
            <X size={18} />
          </button>
        </div>

        {/* File List */}
        <div style={{
          maxHeight: 160, overflowY: 'auto',
          background: 'var(--color-surface-3)',
          border: '1px solid var(--color-border)',
          borderRadius: 10, padding: '0.75rem 1rem',
          display: 'flex', flexDirection: 'column', gap: '0.5rem',
        }}>
          {documents.map(d => (
            <div key={d.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.82rem' }}>
              <span style={{ fontWeight: 500, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '75%' }}>
                📄 {d.filename}
              </span>
              <span style={{
                fontSize: '0.72rem',
                color: d.status === 'placed' ? 'var(--color-success)' : 'var(--color-text-muted)',
              }}>
                {d.status === 'placed' ? 'Filed in Drive' : d.status}
              </span>
            </div>
          ))}
        </div>

        {/* Drive Deletion Checkbox if any doc is placed */}
        {hasPlacedFiles && (
          <div style={{
            background: 'rgba(245, 158, 11, 0.08)',
            border: '1px solid rgba(245, 158, 11, 0.25)',
            borderRadius: 10,
            padding: '0.875rem 1rem',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '0.75rem',
          }}>
            <input
              type="checkbox"
              id="delete-drive-checkbox"
              checked={deleteFromDrive}
              onChange={e => setDeleteFromDrive(e.target.checked)}
              style={{ marginTop: 3, width: 16, height: 16, cursor: 'pointer' }}
            />
            <label htmlFor="delete-drive-checkbox" style={{ fontSize: '0.82rem', cursor: 'pointer', lineHeight: 1.4 }}>
              <strong style={{ color: 'var(--color-warning)' }}>Also delete from Google Drive</strong>
              <div style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)', marginTop: 2 }}>
                Trashes the file(s) in your Google Drive as well as removing from Smart Filer.
              </div>
            </label>
          </div>
        )}

        {/* Actions */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '0.5rem' }}>
          <button
            id="cancel-delete-btn"
            className="btn-secondary"
            onClick={onClose}
            disabled={loading}
            style={{ padding: '0.5rem 1rem', fontSize: '0.85rem' }}
          >
            Cancel
          </button>
          <button
            id="confirm-delete-btn"
            className="btn-danger"
            onClick={handleConfirm}
            disabled={loading}
            style={{ padding: '0.5rem 1.25rem', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}
          >
            <Trash2 size={15} />
            {loading ? 'Deleting...' : 'Delete'}
          </button>
        </div>
      </div>
    </div>
  )
}
