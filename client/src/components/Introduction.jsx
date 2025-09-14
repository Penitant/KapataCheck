import React from 'react'
import { motion } from 'framer-motion'
import { fadeInUp, staggerChildren } from './motionPresets'

export function Introduction() {
  return (
    <section className="container mx-auto px-4 py-20">
      <motion.h1 className='text-center text-5xl font-bold mb-8 text-white'
        initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}>
        Welcome to Chakshu
      </motion.h1>
      <motion.div
        className="max-w-3xl mx-auto text-center text-white space-y-6 backdrop-blur-2xl bg-white/2 rounded-2xl p-8 border border-white/5"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
      >
        <motion.p className="text-xl leading-relaxed" variants={fadeInUp} initial="initial" animate="animate" transition={fadeInUp.transition}>
          Chakshu is an AI-driven system to detect similarities in Expressions of Interest (EoIs) submitted by vendors.
        </motion.p>
        <motion.p className="text-lg leading-relaxed" variants={fadeInUp} initial="initial" animate="animate" transition={{ duration: 0.5, delay: 0.05 }}>
          It compares company profiles and past experience to surface lexical and semantic overlaps that may signal coordination.
        </motion.p>
        <motion.p className="text-lg leading-relaxed" variants={fadeInUp} initial="initial" animate="animate" transition={{ duration: 0.5, delay: 0.1 }}>
          Built in line with GFR 2017 and CVC procurement guidance to support transparency, fairness, and accountability.
        </motion.p>
        <div className="pt-4">
          <motion.p className="text-base text-white font-medium" variants={fadeInUp} initial="initial" animate="animate" transition={{ duration: 0.5, delay: 0.15 }}>
            Upload EoI documents to start the analysis
          </motion.p>
        </div>
      </motion.div>
    </section>        
  )
}
