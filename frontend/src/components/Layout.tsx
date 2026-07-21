import { NavLink, useNavigate } from 'react-router-dom'
import { Upload, Search, Settings, LogOut, FolderOpen, Zap } from 'lucide-react'
import type { User } from '../App'
import { api } from '../api/client'

interface Props {
  user: User | null
  setUser: (u: User | null) => void
  children: React.ReactNode
}

export default function Layout({ user, setUser, children }: Props) {
  const navigate = useNavigate()

  const handleLogout = async () => {
    await api.post('/auth/logout')
    setUser(null)
    navigate('/')
  }

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      {/* Sidebar */}
      <aside style={{
        width: 240,
        background: 'var(--color-surface-2)',
        borderRight: '1px solid var(--color-border)',
        display: 'flex',
        flexDirection: 'column',
        padding: '1.5rem 1rem',
        gap: '0.5rem',
        flexShrink: 0,
      }}>
        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.5rem 0.75rem', marginBottom: '1rem' }}>
          <div style={{
            width: 36, height: 36,
            background: 'linear-gradient(135deg, #4d78ff, #a78bfa)',
            borderRadius: 10,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <FolderOpen size={18} color="#fff" />
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: '0.95rem', lineHeight: 1.2 }}>Smart Filer</div>
            <div style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>AI Drive Organizer</div>
          </div>
        </div>

        {/* Nav links */}
        <NavItem to="/" icon={<Upload size={16} />} label="Upload & Organize" />
        {user && <NavItem to="/search" icon={<Search size={16} />} label="Search" />}
        {user && <NavItem to="/settings" icon={<Settings size={16} />} label="Settings" />}

        {/* Spacer */}
        <div style={{ flex: 1 }} />

        {/* User section */}
        {user ? (
          <div style={{
            borderTop: '1px solid var(--color-border)',
            paddingTop: '1rem',
            display: 'flex',
            flexDirection: 'column',
            gap: '0.75rem',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0 0.25rem' }}>
              {user.picture_url ? (
                <img src={user.picture_url} alt="" style={{ width: 32, height: 32, borderRadius: '50%', border: '2px solid var(--color-brand-500)' }} />
              ) : (
                <div style={{ width: 32, height: 32, borderRadius: '50%', background: 'var(--color-brand-600)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: '0.875rem' }}>
                  {(user.display_name || user.email)[0].toUpperCase()}
                </div>
              )}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: '0.8rem', fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{user.display_name || 'User'}</div>
                <div style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{user.email}</div>
              </div>
            </div>
            <button id="logout-btn" onClick={handleLogout} className="btn-secondary" style={{ width: '100%', justifyContent: 'center', fontSize: '0.8rem' }}>
              <LogOut size={14} /> Sign out
            </button>
          </div>
        ) : (
          <a id="google-signin-btn" href="/auth/google" className="btn-primary" style={{ justifyContent: 'center', textDecoration: 'none' }}>
            <Zap size={16} /> Sign in with Google
          </a>
        )}
      </aside>

      {/* Main content */}
      <main style={{ flex: 1, overflowY: 'auto', padding: '2rem', background: 'var(--color-surface)' }}>
        {children}
      </main>
    </div>
  )
}

function NavItem({ to, icon, label }: { to: string; icon: React.ReactNode; label: string }) {
  return (
    <NavLink
      to={to}
      end
      id={`nav-${label.toLowerCase().replace(/\s+/g, '-')}`}
      style={({ isActive }) => ({
        display: 'flex',
        alignItems: 'center',
        gap: '0.625rem',
        padding: '0.625rem 0.875rem',
        borderRadius: 10,
        textDecoration: 'none',
        fontSize: '0.875rem',
        fontWeight: isActive ? 600 : 400,
        color: isActive ? 'var(--color-brand-400)' : 'var(--color-text-secondary)',
        background: isActive ? 'rgba(77, 120, 255, 0.12)' : 'transparent',
        border: isActive ? '1px solid rgba(77, 120, 255, 0.2)' : '1px solid transparent',
        transition: 'all 0.15s',
      })}
    >
      {icon}
      {label}
    </NavLink>
  )
}
