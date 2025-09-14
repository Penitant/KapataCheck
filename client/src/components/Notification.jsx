import React from 'react'
import { motion } from 'framer-motion'

export default function Notification({ title = 'Notice', message, onClose }) {
  return (
    <motion.div className="max-w-2xl mx-auto mb-6 text-white backdrop-blur-2xl bg-white/2 border border-white/5 rounded-2xl p-4 flex items-start gap-3"
      initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}>
      <div className="flex-1">
        <div className="text-lg font-semibold">{title}</div>
        {message && <div className="text-sm text-white/80 mt-1">{message}</div>}
      </div>
      <motion.button onClick={onClose} className="px-3 py-1 border border-white/30 rounded-lg hover:border-white/60 hover:bg-white/10 transition"
        whileHover={{ y: -1 }} whileTap={{ scale: 0.98 }}>
        Close
      </motion.button>
    </motion.div>
  )
}
