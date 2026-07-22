import { useState } from 'react'
import { CheckSquare, Square, Zap, Trash2 } from 'lucide-react'
import type { DocumentData } from './DocumentCard'

interface Props {
  documents: DocumentData[]
  onBulkApprove: (docIds: string[], threshold: number) => void
  onBulkDelete?: (docIds: string[]) => void
  onDeleteSingle?: (doc: DocumentData) => void
}

export default function BatchTable({ documents, onBulkApprove, onBulkDelete, onDeleteSingle }: Props) {
  const [threshold, setThreshold] = useState(0.9)
  const [selected, setSelected] = useState<Set<string>>(new Set())

  const toggleAll = () => {
    if (selected.size === documents.length) {
      setSelected(new Set())
    } else {
      setSelected(new Set(documents.map(d => d.id)))
    }
  }

  const toggle = (id: string) => {
    setSelected(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  const handleApprove = () => {
    const eligibleSelected = Array.from(selected).filter(id => {
      const doc = documents.find(d => d.id === id)
      const conf = doc?.placement?.candidates?.[0]?.confidence ?? 0
      return conf >= threshold && doc?.status !== 'placed'
    })
    onBulkApprove(eligibleSelected, threshold)
  }

  const handleDelete = () => {
    if (selected.size > 0 && onBulkDelete) {
      onBulkDelete(Array.from(selected))
    }
  }

  if (documents.length === 0) return null

  return (
    <div className="glass-card" style={{ overflow: 'hidden' }}>
      {/* Toolbar */}
      <div style={{
        padding: '1rem 1.25rem',
        borderBottom: '1px solid var(--color-border)',
        display: 'flex',
        alignItems: 'center',
        gap: '1rem',
        flexWrap: 'wrap',
      }}>
        <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>
          Batch Review ({documents.length})
        </span>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginLeft: 'auto' }}>
          {onBulkDelete && selected.size > 0 && (
            <button
              id="bulk-delete-btn"
              className="btn-danger"
              style={{ fontSize: '0.8rem', padding: '0.45rem 0.875rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}
              onClick={handleDelete}
            >
              <Trash2 size={14} /> Delete ({selected.size})
            </button>
          )}

          <label style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)', marginLeft: '0.5rem' }}>
            Approve ≥
          </label>
          <select
            id="batch-threshold-select"
            value={threshold}
            onChange={e => setThreshold(Number(e.target.value))}
            style={{
              background: 'var(--color-surface-3)',
              border: '1px solid var(--color-border)',
              borderRadius: 8,
              color: 'var(--color-text-primary)',
              padding: '0.3rem 0.6rem',
              fontSize: '0.8rem',
            }}
          >
            <option value={0.9}>90%</option>
            <option value={0.85}>85%</option>
            <option value={0.75}>75%</option>
          </select>

          <button
            id="bulk-approve-btn"
            className="btn-primary"
            style={{ fontSize: '0.8rem', padding: '0.45rem 0.875rem' }}
            onClick={handleApprove}
            disabled={selected.size === 0}
          >
            <Zap size={14} /> Approve {selected.size > 0 ? `(${selected.size})` : ''}
          </button>
        </div>
      </div>

      {/* Table */}
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem' }}>
          <thead>
            <tr style={{ background: 'var(--color-surface-3)' }}>
              <th style={{ padding: '0.75rem 1rem', textAlign: 'left', fontWeight: 600, width: 40 }}>
                <button id="batch-toggle-all" onClick={toggleAll} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-text-secondary)', display: 'flex' }}>
                  {selected.size === documents.length && documents.length > 0
                    ? <CheckSquare size={16} />
                    : <Square size={16} />
                  }
                </button>
              </th>
              <th style={{ padding: '0.75rem 1rem', textAlign: 'left', fontWeight: 600 }}>File</th>
              <th style={{ padding: '0.75rem 1rem', textAlign: 'left', fontWeight: 600 }}>Suggested Folder</th>
              <th style={{ padding: '0.75rem 1rem', textAlign: 'left', fontWeight: 600 }}>Confidence</th>
              <th style={{ padding: '0.75rem 1rem', textAlign: 'left', fontWeight: 600 }}>Status</th>
              <th style={{ padding: '0.75rem 1rem', textAlign: 'right', fontWeight: 600 }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {documents.map((doc) => {
              const best = doc.placement?.candidates?.[0]
              const conf = best?.confidence ?? 0
              const badgeClass = conf >= 0.85 ? 'badge-high' : conf >= 0.6 ? 'badge-medium' : 'badge-low'

              return (
                <tr
                  key={doc.id}
                  id={`batch-row-${doc.id}`}
                  style={{
                    borderTop: '1px solid var(--color-border)',
                    background: selected.has(doc.id) ? 'rgba(77,120,255,0.06)' : 'transparent',
                    transition: 'background 0.15s',
                  }}
                >
                  <td style={{ padding: '0.75rem 1rem' }}>
                    <button onClick={() => toggle(doc.id)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: selected.has(doc.id) ? 'var(--color-brand-400)' : 'var(--color-text-muted)', display: 'flex' }}>
                      {selected.has(doc.id) ? <CheckSquare size={16} /> : <Square size={16} />}
                    </button>
                  </td>
                  <td style={{ padding: '0.75rem 1rem', maxWidth: 200, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {doc.filename}
                  </td>
                  <td style={{ padding: '0.75rem 1rem', color: 'var(--color-text-secondary)', maxWidth: 200, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {best?.path ?? '—'}
                  </td>
                  <td style={{ padding: '0.75rem 1rem' }}>
                    {best && <span className={`badge ${badgeClass}`}>{Math.round(conf * 100)}%</span>}
                  </td>
                  <td style={{ padding: '0.75rem 1rem', color: 'var(--color-text-muted)' }}>
                    {doc.status}
                  </td>
                  <td style={{ padding: '0.75rem 1rem', textAlign: 'right' }}>
                    {onDeleteSingle && (
                      <button
                        className="btn-danger"
                        title="Delete file"
                        style={{ padding: '0.3rem 0.5rem', fontSize: '0.75rem', background: 'transparent', border: '1px solid transparent', color: 'var(--color-text-muted)' }}
                        onMouseEnter={e => {
                          e.currentTarget.style.color = 'var(--color-error)'
                          e.currentTarget.style.background = 'rgba(244, 63, 94, 0.12)'
                          e.currentTarget.style.borderColor = 'rgba(244, 63, 94, 0.3)'
                        }}
                        onMouseLeave={e => {
                          e.currentTarget.style.color = 'var(--color-text-muted)'
                          e.currentTarget.style.background = 'transparent'
                          e.currentTarget.style.borderColor = 'transparent'
                        }}
                        onClick={() => onDeleteSingle(doc)}
                      >
                        <Trash2 size={14} />
                      </button>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
