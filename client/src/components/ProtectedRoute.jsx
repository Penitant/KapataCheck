import React from 'react'
import { Navigate } from 'react-router-dom'

// Simple guard: results exist in context or localStorage
export default function ProtectedRoute({ hasData, children }) {
  // Fallback: try to detect persisted data
  let persisted = false
  try {
  const raw = localStorage.getItem('kapatacheck:analysis')
    if (raw) {
      const parsed = JSON.parse(raw)
      persisted = Array.isArray(parsed?.results) && parsed.results.length > 0
    }
  } catch {
    // ignore JSON/storage errors
  }

  if (!hasData && !persisted) {
    return (
      <Navigate to="/" replace state={{ notice: 'Please upload documents first to view feedback.' }} />
    )
  }

  return children
}
