import React from 'react'
import eyeImage from '../assets/eye-search.svg'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { fadeIn, softScale, hoverLift } from './motionPresets'

export function Header() {
  return (
    <motion.header
  className='w-full bg-transparent'
      initial={fadeIn.initial} animate={fadeIn.animate} transition={fadeIn.transition}
    >
      <div className='max-w-7xl mx-auto grid grid-cols-3 items-center px-6 py-4'>
        <motion.div className='text-white text-3xl sm:text-4xl font-extrabold tracking-tight' {...hoverLift}>
          <Link to="/" className="hover:text-sky-300 transition-colors">Aalok</Link>
        </motion.div>
        <motion.div className='flex justify-center items-center' {...softScale}>
          <img src={eyeImage} alt="eyeSearchIcon" className="w-12 h-12 sm:w-14 sm:h-14 brightness-0 invert" />
        </motion.div>
        <motion.div className='text-white text-2xl font-medium text-right' {...hoverLift}>
          <Link to="/feedback" className="hover:text-sky-300 transition-colors">Feedback</Link>
        </motion.div>
      </div>
    </motion.header>
  )
}
