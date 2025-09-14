import React from 'react'
import { motion } from 'framer-motion'

export default function Notification({ title = 'Notice', message, onClose }) {
  return (
    <motion.div className="max-w-2xl mx-auto mb-6 text-white glass rounded-xl p-4 flex items-start gap-3 shadow-xl"
      initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}>
      <div className="flex-1">
        <div className="text-lg font-semibold">{title}</div>
        {message && <div className="text-sm text-white/80 mt-1">{message}</div>}
      </div>
      <motion.button onClick={onClose} className="px-3 py-1 rounded-md bg-gradient-to-r from-cyan-500 to-emerald-500 text-white hover:from-cyan-400 hover:to-emerald-400 transition"
        whileHover={{ y: -1 }} whileTap={{ scale: 0.98 }}>
        Close
      </motion.button>
    </motion.div>
  )
}
