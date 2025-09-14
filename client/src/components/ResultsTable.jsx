import React from 'react'
import { motion } from 'framer-motion'
import { fadeIn, staggerChildren, fadeInUp } from './motionPresets'

/**
 * ResultsTable
 * Props:
 * - rows: array of pair objects with keys { file1, file2, score, risk, learned_prob?, learned_risk? }
 * - editable: if true, show input_score and input_risk editable columns
 * - onChange: (rowId, field, value) => void (required when editable)
 */
export default function ResultsTable({ rows = [], editable = false, onChange }) {
  const hasData = Array.isArray(rows) && rows.length > 0
  return (
    <motion.div
      className="max-w-6xl mx-auto text-white backdrop-blur-2xl bg-white/2 border border-white/5 rounded-2xl p-6"
      initial={fadeIn.initial}
      animate={fadeIn.animate}
      transition={fadeIn.transition}
    >
      {!hasData && (
        <div className="text-white/80 p-6 rounded-lg border border-white/10 bg-white/2">
          <div className="text-lg font-semibold mb-1">No results yet</div>
          <div className="text-sm">Upload documents to see similarity pairs here.</div>
        </div>
      )}

      {hasData && (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-white/90">
            <thead className="text-white/70">
              <tr>
                <th className="py-2 pr-4">File 1</th>
                <th className="py-2 pr-4">File 2</th>
                <th className="py-2 pr-4">Score</th>
                <th className="py-2 pr-4">Risk</th>
                {editable && (
                  <>
                    <th className="py-2 pr-4">Enter Score</th>
                    <th className="py-2 pr-4">Risk Category</th>
                  </>
                )}
              </tr>
            </thead>
            <motion.tbody
              initial={staggerChildren.initial}
              animate={staggerChildren.animate}
            >
              {rows.map((r, i) => (
                <motion.tr
                  key={r.id ?? i}
                  className="border-t border-white/10 hover:bg-white/5"
                  initial={fadeInUp.initial}
                  animate={fadeInUp.animate}
                  transition={{ ...fadeInUp.transition, delay: 0.02 * i }}
                >
                  <td className="py-3 pr-4 align-top max-w-xs truncate" title={r.original_file1 || r.file1}>{r.original_file1 || r.file1}</td>
                  <td className="py-3 pr-4 align-top max-w-xs truncate" title={r.original_file2 || r.file2}>{r.original_file2 || r.file2}</td>
                  <td className="py-3 pr-4 align-top">{typeof (r.score ?? r.learned_prob) === 'number' ? (r.score ?? r.learned_prob).toFixed(3) : '-'}</td>
                  <td className="py-3 pr-4 align-top">{r.risk || r.learned_risk || '-'}</td>
                  {editable && (
                    <>
                      <td className="py-3 pr-4 align-top">
                        <input
                          type="number"
                          step="0.01"
                          min="0"
                          max="1"
                          value={r.input_score ?? ''}
                          onChange={e => onChange?.(r.id ?? i, 'input_score', e.target.value)}
                          className="w-28 bg-transparent border border-white/20 rounded px-2 py-1 focus:outline-none focus:border-white/60"
                        />
                      </td>
                      <td className="py-3 pr-4 align-top">
                        <select
                          value={r.input_risk ?? ''}
                          onChange={e => onChange?.(r.id ?? i, 'input_risk', e.target.value)}
                          className="bg-transparent border border-white/20 rounded px-2 py-1 focus:outline-none focus:border-white/60"
                        >
                          <option value="">Select</option>
                          {['Normal', 'Low', 'Medium', 'High'].map(opt => (
                            <option key={opt} value={opt}>{opt}</option>
                          ))}
                        </select>
                      </td>
                    </>
                  )}
                </motion.tr>
              ))}
            </motion.tbody>
          </table>
        </div>
      )}
    </motion.div>
  )
}
