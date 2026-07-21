import { ChevronRight, Folder } from 'lucide-react'

export interface FolderNode {
  id: string
  drive_folder_id: string
  name: string
  parent_drive_id: string | null
  path: string
}

interface Props {
  folders: FolderNode[]
  onSelect?: (folder: FolderNode) => void
  selectedId?: string
}

function buildTree(folders: FolderNode[]) {
  const map: Record<string, FolderNode & { children: string[] }> = {}
  folders.forEach(f => { map[f.drive_folder_id] = { ...f, children: [] } })
  const roots: string[] = []
  folders.forEach(f => {
    if (f.parent_drive_id && map[f.parent_drive_id]) {
      map[f.parent_drive_id].children.push(f.drive_folder_id)
    } else {
      roots.push(f.drive_folder_id)
    }
  })
  return { map, roots }
}

function FolderRow({
  id, map, depth, onSelect, selectedId,
}: {
  id: string
  map: Record<string, FolderNode & { children: string[] }>
  depth: number
  onSelect?: (f: FolderNode) => void
  selectedId?: string
}) {
  const node = map[id]
  if (!node) return null
  const isSelected = node.drive_folder_id === selectedId

  return (
    <div>
      <button
        id={`folder-tree-item-${node.drive_folder_id}`}
        onClick={() => onSelect?.(node)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          width: '100%',
          padding: `0.35rem 0.75rem`,
          paddingLeft: `${0.75 + depth * 1.25}rem`,
          background: isSelected ? 'rgba(77,120,255,0.15)' : 'transparent',
          border: isSelected ? '1px solid rgba(77,120,255,0.3)' : '1px solid transparent',
          borderRadius: 8,
          cursor: 'pointer',
          textAlign: 'left',
          fontSize: '0.82rem',
          color: isSelected ? 'var(--color-brand-400)' : 'var(--color-text-secondary)',
          transition: 'all 0.15s',
        }}
      >
        {node.children.length > 0 && <ChevronRight size={12} style={{ flexShrink: 0 }} />}
        {node.children.length === 0 && <span style={{ width: 12 }} />}
        <Folder size={13} style={{ flexShrink: 0 }} />
        <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{node.name}</span>
      </button>
      {node.children.map(childId => (
        <FolderRow key={childId} id={childId} map={map} depth={depth + 1} onSelect={onSelect} selectedId={selectedId} />
      ))}
    </div>
  )
}

export default function FolderTree({ folders, onSelect, selectedId }: Props) {
  if (folders.length === 0) {
    return (
      <div style={{ padding: '1rem', color: 'var(--color-text-muted)', fontSize: '0.8rem', textAlign: 'center' }}>
        No folders synced yet. Refresh your Drive tree in Settings.
      </div>
    )
  }

  const { map, roots } = buildTree(folders)

  return (
    <div id="folder-tree" style={{ display: 'flex', flexDirection: 'column', gap: '0.125rem', overflowY: 'auto', maxHeight: 400 }}>
      {roots.map(id => (
        <FolderRow key={id} id={id} map={map} depth={0} onSelect={onSelect} selectedId={selectedId} />
      ))}
    </div>
  )
}
