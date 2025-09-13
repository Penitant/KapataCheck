import React from 'react'

export function Introduction() {
    

    return (
        <section className="container mx-auto px-4 py-4">
            <div className='text-center text-6xl font-bold mt-20'>Welcome to Chakshu</div>
            <div className="max-w-3xl mx-auto mt-8 text-center">
                <p className="text-xl mb-4">
                    Chakshu is an AI-powered system that detects collusion in government procurement Expressions of Interest (EoIs).
                </p>
                <p className="text-lg mb-6">
                    We analyze company profiles and past experience documents for lexical and semantic similarities to identify suspicious patterns that may indicate collusion among vendors.
                </p>
                <p className="text-lg mb-6">
                    As per GFR 2017 and CVC procurement guidelines, this helps strengthen transparency, fairness, and accountability in the procurement process.
                </p>
                <p className="text-base">
                    Upload your EoI documents to begin the analysis and combat practices that reduce opportunities for capable vendors and undermine value for public money.
                </p>
            </div>
        </section>        
    )
}
