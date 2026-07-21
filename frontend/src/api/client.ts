import axios from 'axios'

export const api = axios.create({
  baseURL: '/',
  withCredentials: true, // include httpOnly JWT cookie
  headers: { 'Content-Type': 'application/json' },
})

// Intercept 401 → redirect to login
api.interceptors.response.use(
  r => r,
  err => {
    if (err.response?.status === 401 && !window.location.pathname.includes('/auth')) {
      // Don't redirect on the /auth/me check in App.tsx
    }
    return Promise.reject(err)
  }
)

export const uploadFile = (file: File, onProgress?: (pct: number) => void) => {
  const form = new FormData()
  form.append('file', file)
  return api.post('/documents/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: e => {
      if (onProgress && e.total) {
        onProgress(Math.round((e.loaded * 100) / e.total))
      }
    },
  })
}
