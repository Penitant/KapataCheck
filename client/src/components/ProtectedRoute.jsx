import React from 'react'
import { Navigate, useLocation } from 'react-router-dom'

// Simple guard: results exist in context or localStorage
export default function ProtectedRoute({ hasData, children }) {
  const location = useLocation()
  // Fallback: try to detect persisted data
  let persisted = false
  try {
    const raw = localStorage.getItem('chakshu:analysis')
    if (raw) {
      const parsed = JSON.parse(raw)
      persisted = Array.isArray(parsed?.results) && parsed.results.length > 0
    }
  } catch {}

  if (!hasData && !persisted) {
    return (
      <Navigate to="/" replace state={{ notice: 'Please upload documents first to view feedback.' }} />
    )
  }

  return children
}
