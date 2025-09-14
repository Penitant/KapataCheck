import './App.css'
import { LandingPage } from './pages/LandingPage'
import { useEffect } from 'react'
import Lenis from 'lenis'

function App() {
  useEffect(() => {
    // Initialize Lenis for smooth scrolling
    const lenis = new Lenis({
      duration: 1.2,
      easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      direction: 'vertical',
      gestureDirection: 'vertical',
      smooth: true,
      mouseMultiplier: 1,
      smoothTouch: false,
      touchMultiplier: 2,
      infinite: false,
    })

    function raf(time) {
      lenis.raf(time)
      requestAnimationFrame(raf)
    }

    requestAnimationFrame(raf)

    // Cleanup on unmount
    return () => {
      lenis.destroy()
    }
  }, [])

  return (
    <>
      <LandingPage />
    </>
  )
}

export default App
