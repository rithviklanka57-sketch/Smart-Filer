import { useState } from 'react'
import { FolderPlus, Sparkles, Check, X, Pencil } from 'lucide-react'
import { api } from '../api/client'

export interface ClusterData {
  id: string
  topic_label: string
  suggested_folder_name: string
  member_count: number
  member_document_ids: string[]
}

interface Props {
  cluster: ClusterData
  onAccepted: () => void
  onDismissed: () => void
}

export default function ClusterBanner({ cluster, onAccepted, onDismissed }: Props) {
  const [folderName, setFolderName] = useState(cluster.suggested_folder_name)
  const [editing, setEditing] = useState(false)
  const [loading, setLoading] = useState(false)

  const handleAccept = async () => {
    setLoading(true)
    try {
      await api.post(`/clusters/${cluster.id}/accept`, { folder_name: folderName })
      onAccepted()
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const handleDismiss = async () => {
    try {
      await api.post(`/clusters/${cluster.id}/dismiss`)
      onDismissed()
    } catch (e) {
      console.error(e)
    }
  }

  return (
    <div
      id={`cluster-banner-${cluster.id}`}
      className="fade-in-up"
      style={{
        background: 'linear-gradient(135deg, rgba(77,120,255,0.12), rgba(167,139,250,0.08))',
        border: '1px solid rgba(77,120,255,0.3)',
        borderRadius: 14,
        padding: '1.25rem 1.5rem',
        display: 'flex',
        alignItems: 'center',
        gap: '1rem',
        flexWrap: 'wrap',
      }}
    >
      <div style={{
        width: 40, height: 40, borderRadius: 10, flexShrink: 0,
        background: 'rgba(77,120,255,0.2)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <Sparkles size={20} color="var(--color-brand-400)" />
      </div>

      <div style={{ flex: 1, minWidth: 200 }}>
        <div style={{ fontWeight: 600, fontSize: '0.9rem', marginBottom: '0.25rem' }}>
          {cluster.member_count} related files detected
        </div>
        <div style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)' }}>
          Create a new folder for these {cluster.topic_label} files?
        </div>
      </div>

      {/* Editable folder name */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <FolderPlus size={15} color="var(--color-brand-400)" />
        {editing ? (
          <input
            id={`cluster-name-input-${cluster.id}`}
            className="input"
            value={folderName}
            onChange={e => setFolderName(e.target.value)}
            style={{ width: 200, padding: '0.4rem 0.6rem', fontSize: '0.85rem' }}
            autoFocus
            onBlur={() => setEditing(false)}
          />
        ) : (
          <button
            id={`cluster-edit-name-${cluster.id}`}
            onClick={() => setEditing(true)}
            style={{
              background: 'rgba(77,120,255,0.12)',
              border: '1px solid rgba(77,120,255,0.25)',
              borderRadius: 8, padding: '0.35rem 0.75rem',
              color: 'var(--color-brand-400)', fontWeight: 600, fontSize: '0.85rem',
              cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.4rem',
            }}
          >
            {folderName} <Pencil size={11} />
          </button>
        )}
      </div>

      {/* Actions */}
      <div style={{ display: 'flex', gap: '0.5rem' }}>
        <button
          id={`cluster-accept-${cluster.id}`}
          className="btn-primary"
          style={{ fontSize: '0.8rem', padding: '0.5rem 1rem' }}
          onClick={handleAccept}
          disabled={loading}
        >
          <Check size={14} /> Create folder
        </button>
        <button
          id={`cluster-dismiss-${cluster.id}`}
          className="btn-secondary"
          style={{ fontSize: '0.8rem', padding: '0.5rem 0.875rem' }}
          onClick={handleDismiss}
          disabled={loading}
        >
          <X size={14} />
        </button>
      </div>
    </div>
  )
}
