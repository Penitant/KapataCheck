import React from 'react'
import { UploaderSection } from './UploaderSection'
import { Introduction } from './Introduction'

export function LBody() {
    

    return (
        <section className="container mx-auto px-4 py-4">
            <Introduction />
            <UploaderSection />
        </section>        
    )
}

