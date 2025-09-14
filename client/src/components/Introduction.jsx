import React from 'react'
import { motion } from 'framer-motion'
import { fadeInUp } from './motionPresets'

export function Introduction() {
  return (
    <section className="relative container mx-auto px-4 pt-14 pb-12">
      <div className="absolute inset-x-0 -top-6 flex justify-center pointer-events-none" aria-hidden>
        <div className="h-24 w-[90%] max-w-5xl bg-gradient-to-r from-cyan-500/20 via-sky-400/10 to-emerald-400/20 blur-3xl rounded-full"></div>
      </div>
      <motion.h1 className="text-center text-5xl sm:text-6xl font-extrabold mb-6 text-white tracking-tight"
        initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}>
        Welcome to KapataCheck
      </motion.h1>
      <motion.div
        className="max-w-4xl mx-auto text-center text-white space-y-6 rounded-2xl p-8 sm:p-10 glass"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
      >
        <motion.p className="text-2xl leading-relaxed" variants={fadeInUp} initial="initial" animate="animate" transition={fadeInUp.transition}>
          KapataCheck is an AI-driven system to detect similarities in Expressions of Interest (EoIs) submitted by vendors.
        </motion.p>
        <motion.p className="text-xl leading-relaxed text-slate-200" variants={fadeInUp} initial="initial" animate="animate" transition={{ duration: 0.5, delay: 0.05 }}>
          It compares company profiles and past experience to surface lexical and semantic overlaps that may signal coordination.
        </motion.p>
        <motion.p className="text-xl leading-relaxed text-slate-200" variants={fadeInUp} initial="initial" animate="animate" transition={{ duration: 0.5, delay: 0.1 }}>
          Built in line with GFR 2017 and CVC procurement guidance to support transparency, fairness, and accountability.
        </motion.p>
        <div className="pt-4">
          <motion.p className="text-lg text-white font-medium" variants={fadeInUp} initial="initial" animate="animate" transition={{ duration: 0.5, delay: 0.15 }}>
            Upload EoI documents to start the analysis
          </motion.p>
        </div>
      </motion.div>
    </section>        
  )
}
