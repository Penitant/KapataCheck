import React from 'react'
import eyeImage from '../assets/eye-search.svg'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { fadeIn, softScale, hoverLift } from './motionPresets'

export function Header() {
  return (
    <motion.header className='grid grid-cols-3 items-center p-8 pb-6 relative z-20'
      initial={fadeIn.initial} animate={fadeIn.animate} transition={fadeIn.transition}>
      <motion.div className='text-white text-4xl font-bold' {...hoverLift}>
        <Link to="/" className="hover:text-gray-200 transition-colors">Chakshu</Link>
      </motion.div>
      <motion.div className='flex justify-center items-center' {...softScale}>
        <img src={eyeImage} alt="eyeSearchIcon" className="w-16 h-16 brightness-0 invert" />
      </motion.div>
      <motion.div className='text-white text-2xl font-medium text-right' {...hoverLift}>
        <Link to="/feedback" className="hover:text-gray-200 transition-colors">Feedback</Link>
      </motion.div>
    </motion.header>
  )
}
