import React from 'react'
import { Introduction } from '../components/Introduction'
import { UploaderSection } from '../components/UploaderSection'
import DarkVeil from '../components/DarkVeil'
import ResultsTable from '../components/ResultsTable'
import { useResults } from '../context/ResultsContext'
import { useLocation, useNavigate } from 'react-router-dom'
import Notification from '../components/Notification'

export function LandingPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const notice = location.state?.notice
  const { results } = useResults()

  const clearNotice = () => {
    // Clear only the state while staying on page
    navigate('.', { replace: true, state: {} })
  }

  return (
    <div className="relative min-h-screen">
      <div className="fixed inset-0 z-0 pointer-events-none">
        <DarkVeil hueShift={40} scanlineIntensity={0.06} scanlineFrequency={0}/>
      </div>
      
      <div className="relative z-10">
        {notice && (
          <div className="container mx-auto px-4 pt-6">
            <Notification title="Heads up" message={notice} onClose={clearNotice} />
          </div>
        )}
        <Introduction />
        <UploaderSection />
        {/* First table below the uploader section */}
        <div className="mt-8">
          <ResultsTable rows={(results || []).map((r, idx) => ({ id: idx, ...r }))} />
        </div>
      </div>
    </div>
  )
}
