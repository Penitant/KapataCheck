import './App.css'
import { LandingPage } from './pages/LandingPage'
import { useEffect } from 'react'
import Lenis from 'lenis'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { ResultsProvider, useResults } from './context/ResultsContext'
import { Header } from './components/Header'
import FeedbackPage from './pages/FeedbackPage'
import NotFound from './pages/NotFound'
import ProtectedRoute from './components/ProtectedRoute'

function AppRoutes() {
  const { results } = useResults()
  const hasData = Array.isArray(results) && results.length > 0

  return (
    <BrowserRouter>
      <Header />
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route
          path="/feedback"
          element={
            <ProtectedRoute hasData={hasData}>
              <FeedbackPage />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </BrowserRouter>
  )
}

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
    <ResultsProvider>
      <AppRoutes />
    </ResultsProvider>
  )
}

export default App
