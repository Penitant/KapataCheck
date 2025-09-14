import React, { useEffect, useState } from 'react'
import { useResults } from '../context/ResultsContext'
import { motion } from 'framer-motion'
import { fadeIn } from '../components/motionPresets'
import ResultsTable from '../components/ResultsTable'
import DarkVeil from '../components/DarkVeil'

export default function FeedbackPage() {
  const { results, runId } = useResults()
  const [rows, setRows] = useState([])
  const [prepared, setPrepared] = useState(false)

  useEffect(() => {
    const mapped = (results || []).map((r, idx) => ({
      id: idx,
      ...r,
      input_score: '',
      input_risk: '',
    }))
    setRows(mapped)
  }, [results])

  const handleChange = (id, field, value) => {
    setRows(prev => prev.map(r => (r.id === id ? { ...r, [field]: value } : r)))
  }

  // Prepare snapshot folder when page opens (with empty input columns)
  useEffect(() => {
    const prepare = async () => {
      if (!runId || prepared || !rows.length) return
      try {
        const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'
        await fetch(`${apiBaseUrl}/prepare_feedback_folder`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ run_id: runId, rows: rows.map(r => ({
            file1: r.original_file1 || r.file1,
            file2: r.original_file2 || r.file2,
            input_score: '',
            input_risk: '',
          })) }),
        })
        setPrepared(true)
      } catch (e) {
        console.error('auto prepare feedback folder error', e)
      }
    }
    prepare()
  }, [runId, rows, prepared])

  const submit = async () => {
    const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'
    for (const r of rows) {
      const payload = {
        file1: r.original_file1 || r.file1,
        file2: r.original_file2 || r.file2,
        label: r.input_risk ? 1 : 0,
        scores: {
          jaccard: r.jaccard,
          ngram: r.ngram,
          tfidf: r.tfidf,
          paraphrase: r.paraphrase,
          re_rank_score: r.re_rank_score,
          score: r.input_score || r.learned_prob || r.score,
          risk: r.input_risk || r.learned_risk || r.risk,
          model: 'ui-feedback',
        },
      }
      try {
        await fetch(`${apiBaseUrl}/feedback`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        })
      } catch (e) {
        console.error('feedback error', e)
      }
    }
    // Ask server to snapshot with two new columns
    try {
      const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'
      await fetch(`${apiBaseUrl}/prepare_feedback_folder`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ run_id: runId, rows: rows.map(r => ({
          file1: r.original_file1 || r.file1,
          file2: r.original_file2 || r.file2,
          input_score: r.input_score ?? '',
          input_risk: r.input_risk ?? '',
        })) }),
      })
    } catch (e) {
      console.error('prepare feedback folder error', e)
    }
    alert('Feedback submitted and folder prepared')
  }

  return (
    <div className="relative min-h-screen">
      <div className="fixed inset-0 z-0 pointer-events-none">
        <DarkVeil hueShift={40} scanlineIntensity={0.06} scanlineFrequency={0} />
      </div>
      <div className="relative z-10">
        <section className="container mx-auto px-4 py-10">
          <motion.div className="max-w-6xl mx-auto text-white backdrop-blur-2xl bg-white/2 border border-white/5 rounded-2xl p-6"
            initial={fadeIn.initial} animate={fadeIn.animate} transition={fadeIn.transition}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-2xl font-bold">Feedback</h2>
              <motion.button onClick={submit} className="px-4 py-2 border border-white/40 rounded-lg hover:border-white/70 hover:bg-white/10 transition"
                whileHover={{ y: -2 }} whileTap={{ scale: 0.98 }}>
                Submit All
              </motion.button>
            </div>

            <ResultsTable rows={rows} editable onChange={handleChange} />
          </motion.div>
        </section>
      </div>
    </div>
  )
}
