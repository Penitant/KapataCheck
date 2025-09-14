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
  const riskClass = (risk) => {
    const v = (risk || '').toString().toLowerCase()
    if (v === 'high') return 'bg-rose-900 text-rose-100 ring-1 ring-rose-800'
    if (v === 'medium') return 'bg-orange-900 text-orange-100 ring-1 ring-orange-800'
    if (v === 'low') return 'bg-yellow-900 text-yellow-100 ring-1 ring-yellow-800'
    if (v === 'normal') return 'bg-emerald-900 text-emerald-100 ring-1 ring-emerald-800'
    return 'bg-slate-800 text-slate-100 ring-1 ring-slate-700'
  }
  return (
    <motion.div
      className="max-w-6xl mx-auto text-white bg-slate-900/90 rounded-xl p-0 shadow-xl ring-1 ring-slate-800 overflow-hidden"
      initial={fadeIn.initial}
      animate={fadeIn.animate}
      transition={fadeIn.transition}
    >
      {!hasData && (
        <div className="text-white/80 p-8">
          <div className="text-xl font-semibold mb-1">No results yet</div>
          <div className="text-base">Upload documents to see similarity pairs here.</div>
        </div>
      )}

      {hasData && (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-white">
            <thead className="bg-slate-800/90 text-slate-200">
              <tr>
                <th className="py-4 pl-6 pr-4 text-sm font-semibold tracking-wide uppercase">File 1</th>
                <th className="py-4 pr-4 text-sm font-semibold tracking-wide uppercase">File 2</th>
                <th className="py-4 pr-4 text-sm font-semibold tracking-wide uppercase">Score</th>
                <th className="py-4 pr-4 text-sm font-semibold tracking-wide uppercase">Risk</th>
                {editable && (
                  <>
                    <th className="py-4 pr-4 text-sm font-semibold tracking-wide uppercase">Enter Score</th>
                    <th className="py-4 pr-6 text-sm font-semibold tracking-wide uppercase">Risk Category</th>
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
                  className="border-t border-slate-800 hover:bg-slate-800/70"
                  initial={fadeInUp.initial}
                  animate={fadeInUp.animate}
                  transition={{ ...fadeInUp.transition, delay: 0.02 * i }}
                >
                  <td className="py-4 pl-6 pr-4 align-top max-w-xs truncate text-lg" title={r.original_file1 || r.file1}>{r.original_file1 || r.file1}</td>
                  <td className="py-4 pr-4 align-top max-w-xs truncate text-lg" title={r.original_file2 || r.file2}>{r.original_file2 || r.file2}</td>
                  <td className="py-4 pr-4 align-top text-lg">
                    {typeof (r.score ?? r.learned_prob) === 'number' ? (
                      <span className="inline-flex items-center px-2.5 py-1 rounded-md bg-sky-900 text-sky-200 ring-1 ring-sky-800">
                        {(r.score ?? r.learned_prob).toFixed(3)}
                      </span>
                    ) : '-'}
                  </td>
                  <td className="py-4 pr-4 align-top text-lg">
                    {r.input_risk || r.risk || r.learned_risk ? (
                      <span className={`inline-flex items-center px-2.5 py-1 rounded-md ${riskClass(r.input_risk || r.risk || r.learned_risk)}`}>
                        {r.input_risk || r.risk || r.learned_risk}
                      </span>
                    ) : '-'}
                  </td>
                  {editable && (
                    <>
                      <td className="py-4 pr-4 align-top">
                        <input
                          type="number"
                          step="0.01"
                          min="0"
                          max="1"
                          value={r.input_score ?? ''}
                          onChange={e => onChange?.(r.id ?? i, 'input_score', e.target.value)}
                          className="w-32 bg-slate-900 text-white border border-slate-700 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-sky-500"
                        />
                      </td>
                      <td className="py-4 pr-6 align-top">
                        <select
                          value={r.input_risk ?? ''}
                          onChange={e => onChange?.(r.id ?? i, 'input_risk', e.target.value)}
                          className="bg-slate-900 text-white border border-slate-700 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-teal-500"
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
