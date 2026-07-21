import { useState, useEffect } from 'react'
import { RefreshCw, Trash2, Shield, FolderSync, AlertCircle, CheckCircle } from 'lucide-react'
import { api } from '../api/client'

interface Rule {
  id: string
  pattern_label: string
  target_folder_name: string
  hit_count: number
  created_at: string
}

export default function Settings() {
  const [rules, setRules] = useState<Rule[]>([])
  const [syncing, setSyncing] = useState(false)
  const [syncMsg, setSyncMsg] = useState<string | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)

  useEffect(() => {
    api.get('/rules/').then(r => setRules(r.data)).catch(() => {})
  }, [])

  const handleRefreshFolders = async () => {
    setSyncing(true)
    setSyncMsg(null)
    try {
      await api.post('/folders/refresh')
      setSyncMsg('Folder sync enqueued — your tree will update shortly.')
    } catch {
      setSyncMsg('Failed to enqueue sync. Please try again.')
    } finally {
      setSyncing(false)
    }
  }

  const handleDeleteRule = async (id: string) => {
    await api.delete(`/rules/${id}`)
    setRules(r => r.filter(x => x.id !== id))
    setDeleteConfirm(null)
  }

  return (
    <div style={{ maxWidth: 720, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div>
        <h1 style={{ fontWeight: 800, fontSize: '1.5rem', marginBottom: '0.25rem' }}>Settings</h1>
        <p style={{ color: 'var(--color-text-muted)', fontSize: '0.85rem', margin: 0 }}>
          Manage your Drive connection, learned rules, and preferences.
        </p>
      </div>

      {/* Drive Sync */}
      <section className="glass-card" style={{ padding: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
          <FolderSync size={18} color="var(--color-brand-400)" />
          <h2 style={{ margin: 0, fontSize: '1rem', fontWeight: 700 }}>Google Drive Sync</h2>
        </div>
        <p style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)', margin: '0 0 1rem', lineHeight: 1.6 }}>
          Smart Filer caches your Drive folder tree to suggest placements without hammering the Drive API.
          If you've reorganized your Drive recently, click Refresh to re-sync.
        </p>
        <button
          id="refresh-folders-btn"
          className="btn-primary"
          onClick={handleRefreshFolders}
          disabled={syncing}
          style={{ fontSize: '0.85rem' }}
        >
          <RefreshCw size={14} className={syncing ? 'status-pulse' : ''} />
          {syncing ? 'Syncing…' : 'Refresh folder tree'}
        </button>
        {syncMsg && (
          <div style={{
            marginTop: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem',
            fontSize: '0.8rem',
            color: syncMsg.includes('Fail') ? 'var(--color-error)' : 'var(--color-success)',
          }}>
            {syncMsg.includes('Fail') ? <AlertCircle size={14} /> : <CheckCircle size={14} />}
            {syncMsg}
          </div>
        )}
      </section>

      {/* OAuth Scope Info */}
      <section className="glass-card" style={{ padding: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
          <Shield size={18} color="var(--color-success)" />
          <h2 style={{ margin: 0, fontSize: '1rem', fontWeight: 700 }}>Privacy & Permissions</h2>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem', fontSize: '0.85rem', color: 'var(--color-text-secondary)' }}>
          {[
            ['drive.file', 'Read/write only files created by this app — not your entire Drive'],
            ['drive.metadata.readonly', 'Read folder names and structure to suggest placements'],
            ['openid + profile + email', 'Identify your account — no password stored'],
          ].map(([scope, desc]) => (
            <div key={scope} style={{ display: 'flex', gap: '0.75rem' }}>
              <code style={{
                background: 'var(--color-surface-3)',
                border: '1px solid var(--color-border)',
                borderRadius: 6, padding: '0.1rem 0.5rem',
                fontSize: '0.75rem', color: 'var(--color-brand-400)',
                flexShrink: 0, alignSelf: 'flex-start', marginTop: 1,
              }}>{scope}</code>
              <span style={{ lineHeight: 1.5 }}>{desc}</span>
            </div>
          ))}
        </div>
        <p style={{ marginTop: '1rem', fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
          Your refresh token is encrypted at rest and never sent to the frontend. Sign out anytime to revoke access.
        </p>
      </section>

      {/* Learned Rules */}
      <section className="glass-card" style={{ padding: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.25rem' }}>
          <span style={{ fontSize: '1.1rem' }}>🧠</span>
          <h2 style={{ margin: 0, fontSize: '1rem', fontWeight: 700 }}>Learned Placement Rules</h2>
          <span style={{
            marginLeft: 'auto',
            background: 'var(--color-surface-3)',
            border: '1px solid var(--color-border)',
            borderRadius: 9999, padding: '0.15rem 0.6rem',
            fontSize: '0.75rem', color: 'var(--color-text-muted)',
          }}>{rules.length} rules</span>
        </div>
        <p style={{ fontSize: '0.82rem', color: 'var(--color-text-muted)', margin: '0 0 1rem' }}>
          These rules are built from your corrections — delete any to reset that filing behavior.
        </p>

        {rules.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--color-text-muted)', fontSize: '0.85rem' }}>
            No learned rules yet. Override a placement suggestion to create one.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem' }}>
            {rules.map(rule => (
              <div
                key={rule.id}
                id={`rule-row-${rule.id}`}
                style={{
                  display: 'flex', alignItems: 'center', gap: '0.875rem',
                  padding: '0.875rem 1rem',
                  background: 'var(--color-surface-3)',
                  border: '1px solid var(--color-border)',
                  borderRadius: 10,
                }}
              >
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: 600, fontSize: '0.85rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {rule.pattern_label || 'Unnamed rule'}
                  </div>
                  <div style={{ fontSize: '0.78rem', color: 'var(--color-text-muted)', marginTop: '0.2rem' }}>
                    → {rule.target_folder_name} · {rule.hit_count} match{rule.hit_count !== 1 ? 'es' : ''}
                  </div>
                </div>
                {deleteConfirm === rule.id ? (
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <button
                      id={`delete-rule-confirm-${rule.id}`}
                      className="btn-danger"
                      style={{ fontSize: '0.78rem', padding: '0.35rem 0.75rem' }}
                      onClick={() => handleDeleteRule(rule.id)}
                    >
                      Delete
                    </button>
                    <button
                      id={`delete-rule-cancel-${rule.id}`}
                      className="btn-secondary"
                      style={{ fontSize: '0.78rem', padding: '0.35rem 0.75rem' }}
                      onClick={() => setDeleteConfirm(null)}
                    >
                      Cancel
                    </button>
                  </div>
                ) : (
                  <button
                    id={`delete-rule-${rule.id}`}
                    className="btn-danger"
                    style={{ fontSize: '0.78rem', padding: '0.35rem 0.6rem' }}
                    onClick={() => setDeleteConfirm(rule.id)}
                  >
                    <Trash2 size={13} />
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
