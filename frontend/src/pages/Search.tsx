import { useState } from 'react'
import { Search as SearchIcon, FileText, ExternalLink, Loader } from 'lucide-react'
import { api } from '../api/client'

interface SearchResult {
  id: string
  filename: string
  doc_type: string
  summary: string
  snippet: string
  drive_file_id: string
  drive_link: string
  created_at: string
}

export default function Search() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return
    setLoading(true)
    setSearched(true)
    try {
      const res = await api.get('/search/', { params: { q: query, limit: 20 } })
      setResults(res.data.results)
    } catch {
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <h1 style={{ fontWeight: 800, fontSize: '1.5rem', marginBottom: '0.5rem' }}>
        Semantic Search
      </h1>
      <p style={{ color: 'var(--color-text-muted)', fontSize: '0.85rem', marginBottom: '1.5rem' }}>
        Search your filed documents using natural language — no need to remember exact filenames.
      </p>

      {/* Search bar */}
      <form id="search-form" onSubmit={handleSearch} style={{ display: 'flex', gap: '0.75rem', marginBottom: '2rem' }}>
        <div style={{ flex: 1, position: 'relative' }}>
          <SearchIcon size={16} style={{ position: 'absolute', left: '0.875rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--color-text-muted)' }} />
          <input
            id="search-input"
            className="input"
            style={{ paddingLeft: '2.5rem' }}
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="e.g. that contract about the office lease..."
          />
        </div>
        <button id="search-submit-btn" type="submit" className="btn-primary" disabled={loading || !query.trim()}>
          {loading ? <Loader size={15} className="status-pulse" /> : <SearchIcon size={15} />}
          Search
        </button>
      </form>

      {/* Results */}
      {loading && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {[...Array(3)].map((_, i) => (
            <div key={i} className="glass-card" style={{ padding: '1.25rem' }}>
              <div className="skeleton" style={{ height: 16, width: '60%', marginBottom: '0.5rem' }} />
              <div className="skeleton" style={{ height: 12, width: '100%', marginBottom: '0.4rem' }} />
              <div className="skeleton" style={{ height: 12, width: '80%' }} />
            </div>
          ))}
        </div>
      )}

      {!loading && searched && results.length === 0 && (
        <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--color-text-muted)' }}>
          <SearchIcon size={32} style={{ marginBottom: '0.75rem', opacity: 0.3 }} />
          <p>No results found for "{query}"</p>
        </div>
      )}

      {!loading && results.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.875rem' }}>
          <p style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', margin: 0 }}>
            {results.length} result{results.length !== 1 ? 's' : ''}
          </p>
          {results.map(r => (
            <div key={r.id} id={`search-result-${r.id}`} className="glass-card fade-in-up" style={{ padding: '1.25rem' }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
                <div style={{
                  width: 36, height: 36, borderRadius: 10,
                  background: 'var(--color-surface-3)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                }}>
                  <FileText size={16} color="var(--color-brand-400)" />
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
                    <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>{r.filename}</span>
                    {r.doc_type && (
                      <span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                        {r.doc_type}
                      </span>
                    )}
                    {r.drive_link && (
                      <a href={r.drive_link} target="_blank" rel="noreferrer"
                        id={`search-open-drive-${r.id}`}
                        style={{ marginLeft: 'auto', display: 'inline-flex', alignItems: 'center', gap: '0.3rem', fontSize: '0.78rem', color: 'var(--color-brand-400)', textDecoration: 'none' }}>
                        <ExternalLink size={12} /> Open in Drive
                      </a>
                    )}
                  </div>
                  {r.snippet && (
                    <p style={{ margin: '0.5rem 0 0', fontSize: '0.82rem', color: 'var(--color-text-secondary)', lineHeight: 1.6 }}>
                      …{r.snippet}…
                    </p>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {!searched && (
        <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--color-text-muted)' }}>
          <SearchIcon size={40} style={{ marginBottom: '1rem', opacity: 0.15 }} />
          <p style={{ fontSize: '0.9rem' }}>Type a query above to search your filed documents.</p>
          <p style={{ fontSize: '0.8rem', marginTop: '0.25rem' }}>
            Try: "invoice from last month", "contract about office", "my resume"
          </p>
        </div>
      )}
    </div>
  )
}
