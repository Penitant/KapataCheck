import React from 'react'
import { Header } from '../components/Header'
import { Introduction } from '../components/Introduction'
import { UploaderSection } from '../components/UploaderSection'
import DarkVeil from '../components/DarkVeil'

export function LandingPage() {
    

    return (
        <div className="relative min-h-screen">
            <div className="fixed inset-0 z-0">
                <DarkVeil hueShift={40} scanlineIntensity={0.06} scanlineFrequency={0}/>
            </div>
            
            <div className="relative z-10">
                <Header />
                <Introduction />
                <UploaderSection />
            </div>
        </div>
    )
}
