import React, { createContext, useContext, useState, useEffect } from 'react'

const ResultsContext = createContext(null)

export function ResultsProvider({ children }) {
  const [results, setResults] = useState([])
  const [meta, setMeta] = useState({})
  const [runId, setRunId] = useState(null)

  // Hydrate from localStorage on first mount
  useEffect(() => {
    try {
      const raw = localStorage.getItem('chakshu:analysis')
      if (raw) {
        const payload = JSON.parse(raw)
        setResults(payload?.results || [])
        setMeta({
          model: payload?.model,
          paraphrase: payload?.paraphrase,
          cross_encoder: payload?.cross_encoder,
          hash: payload?.hash,
          hybrid: payload?.hybrid,
          cluster: payload?.cluster,
          ce_top_k: payload?.ce_top_k,
          count: payload?.count,
          timings: payload?.timings,
        })
        setRunId(payload?.run_id || null)
      }
    } catch {}
  }, [])

  const storePayload = (payload) => {
    setResults(payload?.results || [])
    const newMeta = {
      model: payload?.model,
      paraphrase: payload?.paraphrase,
      cross_encoder: payload?.cross_encoder,
      hash: payload?.hash,
      hybrid: payload?.hybrid,
      cluster: payload?.cluster,
      ce_top_k: payload?.ce_top_k,
      count: payload?.count,
      timings: payload?.timings,
    }
    setMeta(newMeta)
    setRunId(payload?.run_id || null)
    try {
      localStorage.setItem('chakshu:analysis', JSON.stringify({ results: payload?.results || [], ...newMeta, run_id: payload?.run_id || null }))
    } catch {}
  }

  const clear = () => {
    setResults([])
    setMeta({})
    try { localStorage.removeItem('chakshu:analysis') } catch {}
  }

  return (
    <ResultsContext.Provider value={{ results, meta, runId, storePayload, clear }}>
      {children}
    </ResultsContext.Provider>
  )
}

export function useResults() {
  const ctx = useContext(ResultsContext)
  if (!ctx) throw new Error('useResults must be used within ResultsProvider')
  return ctx
}
