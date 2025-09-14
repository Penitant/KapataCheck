export const fadeInUp = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1] }
}

export const fadeIn = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  transition: { duration: 0.5, ease: 'easeOut' }
}

export const softScale = {
  initial: { opacity: 0, scale: 0.98 },
  animate: { opacity: 1, scale: 1 },
  transition: { duration: 0.4, ease: [0.16, 1, 0.3, 1] }
}

export const staggerChildren = {
  initial: {},
  animate: { transition: { staggerChildren: 0.06, delayChildren: 0.05 } }
}

export const hoverLift = {
  whileHover: { y: -2, scale: 1.01 },
  transition: { type: 'spring', stiffness: 300, damping: 20 }
}
