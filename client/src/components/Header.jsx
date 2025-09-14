import React from 'react'
import eyeImage from '../assets/eye-search.svg'

export function Header() {
    

    return (
        <header className='grid grid-cols-3 items-center p-8 pb-6'>
            <div className='text-white text-4xl font-bold'>Chakshu</div>
            <div className='flex justify-center items-center'>
                <img src={eyeImage} alt="eyeSearchIcon" className="w-16 h-16 brightness-0 invert" />
            </div>
            <div className='text-white text-3xl font-medium hover:text-gray-200 transition-colors cursor-pointer text-right'>About Us</div>
        </header>
    )
}
