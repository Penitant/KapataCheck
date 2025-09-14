import React from 'react'

export function Introduction() {
    

    return (
        <section className="container mx-auto px-4 py-20">
            <h1 className='text-center text-5xl font-bold mb-8 text-white'>
                Welcome to Chakshu
            </h1>
            <div className="max-w-3xl mx-auto text-center text-white space-y-6 backdrop-blur-2xl bg-white/2 rounded-2xl p-8 border border-white/5">
                <p className="text-xl leading-relaxed">
                    Chakshu is an AI-driven system to detect similarities in Expressions of Interest (EoIs) submitted by vendors.
                </p>
                <p className="text-lg leading-relaxed">
                    It compares company profiles and past experience to surface lexical and semantic overlaps that may signal coordination.
                </p>
                <p className="text-lg leading-relaxed">
                    Built in line with GFR 2017 and CVC procurement guidance to support transparency, fairness, and accountability.
                </p>
                <div className="pt-4">
                    <p className="text-base text-white font-medium">
                        Upload EoI documents to start the analysis
                    </p>
                </div>
            </div>
        </section>        
    )
}
