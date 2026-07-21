import { Routes, Route, Navigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { api } from './api/client'
import Home from './pages/Home'
import Search from './pages/Search'
import Settings from './pages/Settings'
import Layout from './components/Layout'

export interface User {
  id: string
  email: string
  display_name: string
  picture_url: string
}

export default function App() {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get('/auth/me')
      .then(r => setUser(r.data))
      .catch(() => setUser(null))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--color-surface)',
      }}>
        <div style={{ textAlign: 'center' }}>
          <div className="skeleton" style={{ width: 48, height: 48, borderRadius: '50%', margin: '0 auto 16px' }} />
          <p style={{ color: 'var(--color-text-muted)', fontSize: '0.875rem' }}>Loading...</p>
        </div>
      </div>
    )
  }

  return (
    <Layout user={user} setUser={setUser}>
      <Routes>
        <Route path="/" element={<Home user={user} />} />
        <Route path="/search" element={user ? <Search /> : <Navigate to="/" />} />
        <Route path="/settings" element={user ? <Settings /> : <Navigate to="/" />} />
      </Routes>
    </Layout>
  )
}
