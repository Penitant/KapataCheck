import React from 'react'
import eyeImage from '../assets/eye-search.svg'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { fadeIn, softScale, hoverLift } from './motionPresets'

export function Header() {
  return (
    <motion.header
      className="sticky top-0 z-50 w-full/ bg-transparent"
      initial={fadeIn.initial} animate={fadeIn.animate} transition={fadeIn.transition}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        <div className="glass rounded-2xl mt-4 mb-2">
          <div className="grid grid-cols-3 items-center px-5 py-3">
            <motion.div className="text-white text-2xl sm:text-3xl font-extrabold tracking-tight" {...hoverLift}>
              <Link to="/" className="group relative inline-flex items-center">
                KapataCheck
                <span className="ml-2 inline-block w-1.5 h-1.5 rounded-full bg-cyan-400/90 shadow-[0_0_12px_rgba(34,211,238,0.7)]"></span>
              </Link>
            </motion.div>
            <motion.div className="flex justify-center items-center" {...softScale}>
              <img src={eyeImage} alt="eyeSearchIcon" className="w-10 h-10 sm:w-12 sm:h-12 brightness-0 invert drop-shadow-[0_0_18px_rgba(34,211,238,.2)]" />
            </motion.div>
            <motion.nav className="text-right" {...hoverLift}>
              <Link to="/feedback" className="relative inline-block text-white/90 hover:text-cyan-300 transition-colors text-lg font-medium">
                Feedback
                <span className="block absolute -bottom-1 left-0 h-px w-0 bg-gradient-to-r from-cyan-400 to-emerald-400 transition-all group-hover:w-full"></span>
              </Link>
            </motion.nav>
          </div>
        </div>
      </div>
    </motion.header>
  )
}
