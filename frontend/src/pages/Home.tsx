import { useState, useEffect, useRef, useCallback } from 'react'
import { Zap, RefreshCw, LayoutGrid, List, Wifi, WifiOff } from 'lucide-react'
import { api, uploadFile } from '../api/client'
import type { User } from '../App'
import UploadDropzone from '../components/UploadDropzone'
import DocumentCard, { type DocumentData } from '../components/DocumentCard'
import ClusterBanner, { type ClusterData } from '../components/ClusterBanner'
import BatchTable from '../components/BatchTable'
import DeleteModal from '../components/DeleteModal'

interface Props {
  user: User | null
}

export default function Home({ user }: Props) {
  const [documents, setDocuments] = useState<DocumentData[]>([])
  const [clusters, setClusters] = useState<ClusterData[]>([])
  const [uploading, setUploading] = useState(false)
  const [view, setView] = useState<'cards' | 'table'>('cards')
  const [wsConnected, setWsConnected] = useState(false)
  const [docsToDelete, setDocsToDelete] = useState<DocumentData[]>([])
  const [deleteLoading, setDeleteLoading] = useState(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // ── Data fetchers ─────────────────────────────────────────────────────────
  const fetchDocuments = useCallback(async () => {
    try {
      const res = await api.get('/documents/')
      // Enrich non-placed docs with placement details
      const withPlacements = await Promise.all(
        res.data.map(async (d: DocumentData) => {
          if (d.status !== 'placed' && d.status !== 'error') {
            try {
              const detail = await api.get(`/documents/${d.id}`)
              return detail.data
            } catch {
              return d
            }
          }
          return d
        })
      )
      setDocuments(withPlacements)
    } catch { /* not authenticated */ }
  }, [])

  const fetchClusters = useCallback(async () => {
    try {
      const res = await api.get('/clusters/')
      setClusters(res.data)
    } catch { /* ignore */ }
  }, [])

  const fetchOneDocument = useCallback(async (docId: string) => {
    try {
      const detail = await api.get(`/documents/${docId}`)
      setDocuments(prev => prev.map(d => d.id === docId ? detail.data : d))
    } catch { /* ignore */ }
  }, [])

  // ── WebSocket (Phase 9 — live per-file status updates) ────────────────────
  const connectWS = useCallback((userId: string) => {
    // Don't open a second connection
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${proto}://${window.location.host}/documents/ws/${userId}`)
    wsRef.current = ws

    ws.onopen = () => {
      setWsConnected(true)
      // Clear fallback poll — WS is live
      if (pollRef.current) {
        clearInterval(pollRef.current)
        pollRef.current = null
      }
    }

    ws.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data) as { document_id?: string; status?: string }
        if (!msg.document_id || !msg.status) return

        // Instantly update status on the existing card
        setDocuments(prev =>
          prev.map(d => d.id === msg.document_id ? { ...d, status: msg.status! } : d)
        )

        // When processing finishes, fetch full detail (placement, summary, etc.)
        const terminalStatuses = ['needs_input', 'pending', 'placed', 'error']
        if (terminalStatuses.includes(msg.status)) {
          fetchOneDocument(msg.document_id)
          if (msg.status !== 'error') fetchClusters()
        }
      } catch { /* ignore malformed */ }
    }

    // Keep-alive ping every 25 s
    const pingId = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) ws.send('ping')
    }, 25000)

    ws.onclose = () => {
      setWsConnected(false)
      clearInterval(pingId)
      // Start fallback polling while disconnected
      startFallbackPoll()
      // Reconnect after 4 s
      reconnectRef.current = setTimeout(() => connectWS(userId), 4000)
    }

    ws.onerror = () => ws.close()
  }, [fetchOneDocument, fetchClusters]) // eslint-disable-line react-hooks/exhaustive-deps

  // ── Fallback polling (only active when WS is disconnected) ────────────────
  const startFallbackPoll = useCallback(() => {
    if (pollRef.current) return
    pollRef.current = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        clearInterval(pollRef.current!)
        pollRef.current = null
        return
      }
      setDocuments(prev => {
        const hasPending = prev.some(d =>
          ['pending', 'extracting', 'classifying'].includes(d.status)
        )
        if (hasPending) {
          fetchDocuments()
          fetchClusters()
        }
        return prev
      })
    }, 5000)
  }, [fetchDocuments, fetchClusters])

  useEffect(() => {
    if (!user) return
    fetchDocuments()
    fetchClusters()
    connectWS(user.id)

    return () => {
      wsRef.current?.close()
      if (pollRef.current) clearInterval(pollRef.current)
      if (reconnectRef.current) clearTimeout(reconnectRef.current)
    }
  }, [user]) // eslint-disable-line react-hooks/exhaustive-deps

  // ── Upload handler ────────────────────────────────────────────────────────
  const handleFiles = async (files: File[]) => {
    if (!user) return
    setUploading(true)
    for (const file of files) {
      try {
        const res = await uploadFile(file)
        const newDoc: DocumentData = {
          id: res.data.document_id,
          filename: file.name,
          status: 'pending',
        }
        // Optimistically add the card immediately
        setDocuments(prev => [newDoc, ...prev])
      } catch (e: any) {
        console.error('Upload failed', e)
        const msg = e.response?.data?.detail || e.message || 'Upload failed'
        alert(`Upload failed for ${file.name}: ${msg}`)
      }
    }
    setUploading(false)
  }

  const handleAnswer = async (docId: string, folderId: string, folderName: string) => {
    await api.post(`/documents/${docId}/answer`, {
      chosen_folder_id: folderId,
      chosen_folder_name: folderName,
    })
    fetchOneDocument(docId)
  }

  const handleConfirm = async (docId: string, folderId: string, folderName: string) => {
    try {
      const res = await api.post(`/documents/${docId}/confirm`, {
        folder_id: folderId,
        folder_name: folderName,
      })
      setDocuments(prev =>
        prev.map(d => d.id === docId ? { ...d, status: 'placed', drive_link: res.data.web_view_link } : d)
      )
    } catch (e: any) {
      // Duplicate file detected
      if (e.response?.data?.duplicate) {
        const dup = e.response.data
        const choice = window.confirm(
          `"${dup.existing_file.name}" already exists in this folder.\n\nOK = Replace it\nCancel = Keep both`
        )
        await api.post(`/documents/${docId}/confirm`, {
          folder_id: folderId,
          folder_name: folderName,
          replace_file_id: choice ? dup.existing_file.id : undefined,
        })
        fetchOneDocument(docId)
      }
    }
  }

  const handleBulkApprove = async (docIds: string[], _threshold: number) => {
    for (const id of docIds) {
      const doc = documents.find(d => d.id === id)
      const best = doc?.placement?.candidates?.[0]
      if (best) await handleConfirm(id, best.folder_id, best.folder_name)
    }
  }

  // ── Delete handlers ───────────────────────────────────────────────────────
  const openDeleteModalForDoc = (doc: DocumentData) => {
    setDocsToDelete([doc])
  }

  const openDeleteModalForBatch = (docIds: string[]) => {
    const targetDocs = documents.filter(d => docIds.includes(d.id))
    setDocsToDelete(targetDocs)
  }

  const handleConfirmDelete = async (deleteFromDrive: boolean) => {
    if (docsToDelete.length === 0) return
    setDeleteLoading(true)
    try {
      if (docsToDelete.length === 1) {
        const doc = docsToDelete[0]
        await api.delete(`/documents/${doc.id}`, { params: { delete_from_drive: deleteFromDrive } })
        setDocuments(prev => prev.filter(d => d.id !== doc.id))
      } else {
        const docIds = docsToDelete.map(d => d.id)
        await api.post('/documents/batch-delete', {
          document_ids: docIds,
          delete_from_drive: deleteFromDrive,
        })
        setDocuments(prev => prev.filter(d => !docIds.includes(d.id)))
      }
      setDocsToDelete([])
    } catch (e: any) {
      console.error('Delete failed', e)
      alert(e.response?.data?.detail || 'Failed to delete document(s)')
    } finally {
      setDeleteLoading(false)
    }
  }

  // ── Unauthenticated landing ───────────────────────────────────────────────
  if (!user) {
    return (
      <div style={{ maxWidth: 640, margin: '0 auto', paddingTop: '4rem', textAlign: 'center' }}>
        <div style={{ marginBottom: '2rem' }}>
          <div style={{
            width: 80, height: 80, borderRadius: 20,
            background: 'linear-gradient(135deg, #4d78ff, #a78bfa)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            margin: '0 auto 1.5rem',
            boxShadow: '0 0 40px rgba(77,120,255,0.4)',
          }}>
            <Zap size={38} color="#fff" />
          </div>
          <h1 style={{ fontSize: '2.5rem', fontWeight: 800, margin: '0 0 0.75rem', lineHeight: 1.2 }}>
            <span className="gradient-text">Smart Drive Filer</span>
          </h1>
          <p style={{ fontSize: '1.05rem', color: 'var(--color-text-secondary)', lineHeight: 1.6, margin: '0 0 2rem' }}>
            Upload any document. AI analyzes, categorizes, and files it in exactly the right Google Drive folder — with full control at every step.
          </p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '2.5rem', textAlign: 'left' }}>
          {[
            ['🧠 AI Classification', 'Identifies document type and key entities automatically'],
            ['📁 Smart Placement', 'Suggests the best folder with confidence scores'],
            ['✨ New Folder Clusters', 'Detects related unfiled docs and proposes a new folder'],
            ['🔍 Semantic Search', 'Find any document with natural language queries'],
          ].map(([title, desc]) => (
            <div key={title} className="glass-card" style={{ padding: '1rem' }}>
              <div style={{ fontWeight: 600, fontSize: '0.875rem', marginBottom: '0.35rem' }}>{title}</div>
              <div style={{ fontSize: '0.78rem', color: 'var(--color-text-muted)', lineHeight: 1.5 }}>{desc}</div>
            </div>
          ))}
        </div>

        <a id="hero-signin-btn" href="/auth/google" className="btn-primary" style={{ textDecoration: 'none', padding: '0.875rem 2rem', fontSize: '1rem' }}>
          <Zap size={18} /> Sign in with Google to get started
        </a>
      </div>
    )
  }

  const pendingCount = documents.filter(d =>
    ['extracting', 'classifying'].includes(d.status) || (d.status === 'pending' && !d.placement)
  ).length

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <div>
          <h1 style={{ margin: 0, fontWeight: 800, fontSize: '1.5rem' }}>
            Hi, {user.display_name?.split(' ')[0] || 'there'} 👋
          </h1>
          <p style={{ margin: '0.25rem 0 0', fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>
            Upload documents to file them automatically into your Google Drive.
          </p>
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          {/* Live connection indicator */}
          <div
            id="ws-status-indicator"
            title={wsConnected ? 'Live updates connected' : 'Polling for updates'}
            style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', fontSize: '0.72rem', color: wsConnected ? 'var(--color-success)' : 'var(--color-text-muted)' }}
          >
            {wsConnected ? <Wifi size={13} /> : <WifiOff size={13} />}
            {wsConnected ? 'Live' : 'Polling'}
          </div>
          <button id="view-cards-btn" className="btn-secondary" style={{ padding: '0.5rem 0.75rem' }} onClick={() => setView('cards')}>
            <LayoutGrid size={15} />
          </button>
          <button id="view-table-btn" className="btn-secondary" style={{ padding: '0.5rem 0.75rem' }} onClick={() => setView('table')}>
            <List size={15} />
          </button>
          <button id="refresh-docs-btn" className="btn-secondary" style={{ fontSize: '0.8rem' }} onClick={() => { fetchDocuments(); fetchClusters() }}>
            <RefreshCw size={14} /> Refresh
          </button>
        </div>
      </div>

      {/* Upload dropzone */}
      <UploadDropzone onFiles={handleFiles} disabled={uploading} />

      {/* Processing status */}
      {pendingCount > 0 && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: '0.75rem',
          padding: '0.75rem 1rem',
          background: 'rgba(56, 189, 248, 0.08)',
          border: '1px solid rgba(56, 189, 248, 0.2)',
          borderRadius: 10, fontSize: '0.85rem', color: 'var(--color-info)',
        }}>
          <RefreshCw size={15} className="status-pulse" />
          Processing {pendingCount} file{pendingCount > 1 ? 's' : ''} in the background
          {wsConnected ? ' — updates are live.' : ' — checking every 5 seconds.'}
        </div>
      )}

      {/* Cluster banners */}
      {clusters.map(cluster => (
        <ClusterBanner
          key={cluster.id}
          cluster={cluster}
          onAccepted={() => { setClusters(c => c.filter(x => x.id !== cluster.id)); fetchDocuments() }}
          onDismissed={() => setClusters(c => c.filter(x => x.id !== cluster.id))}
        />
      ))}

      {/* Documents */}
      {documents.length > 0 ? (
        view === 'cards' ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(380px, 1fr))', gap: '1rem' }}>
            {documents.map(doc => (
              <DocumentCard
                key={doc.id}
                doc={doc}
                onAnswer={(fId, fName) => handleAnswer(doc.id, fId, fName)}
                onConfirm={(fId, fName) => handleConfirm(doc.id, fId, fName)}
                onDelete={openDeleteModalForDoc}
              />
            ))}
          </div>
        ) : (
          <BatchTable
            documents={documents}
            onBulkApprove={handleBulkApprove}
            onBulkDelete={openDeleteModalForBatch}
            onDeleteSingle={openDeleteModalForDoc}
          />
        )
      ) : (
        <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--color-text-muted)' }}>
          <p style={{ fontSize: '0.9rem' }}>No documents yet. Upload your first file above.</p>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      <DeleteModal
        isOpen={docsToDelete.length > 0}
        documents={docsToDelete}
        onClose={() => setDocsToDelete([])}
        onConfirm={handleConfirmDelete}
        loading={deleteLoading}
      />
    </div>
  )
}
