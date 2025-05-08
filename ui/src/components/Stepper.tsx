import React from 'react'

interface IStepper {
    activeStep: number;
}
  

const Stepper : React.FC<IStepper> = () => {
  return (

<ul className="relative flex flex-col md:flex-row gap-2">

  <li className="md:shrink md:basis-0 flex-1 group flex gap-x-2 md:block">
    <div className="min-w-7 min-h-7 flex flex-col items-center md:w-full md:inline-flex md:flex-wrap md:flex-row text-xs align-middle">
      <span className="size-7 flex justify-center items-center shrink-0 bg-gray-100 font-medium text-gray-800 rounded-full dark:bg-neutral-700 dark:text-white">
        1
      </span>
      <div className="mt-2 w-px h-full md:mt-0 md:ms-2 md:w-full md:h-px md:flex-1 bg-gray-200 group-last:hidden dark:bg-neutral-700"></div>
    </div>
    <div className="grow md:grow-0 md:mt-3 pb-5">
      <span className="block text-sm font-medium text-gray-800 dark:text-white">
        Step
      </span>
      <p className="text-sm text-gray-500 dark:text-neutral-500">
        This is a description text.
      </p>
    </div>
  </li>

  <li className="md:shrink md:basis-0 flex-1 group flex gap-x-2 md:block">
    <div className="min-w-7 min-h-7 flex flex-col items-center md:w-full md:inline-flex md:flex-wrap md:flex-row text-xs align-middle">
      <span className="size-7 flex justify-center items-center shrink-0 bg-gray-100 font-medium text-gray-800 rounded-full dark:bg-neutral-700 dark:text-white">
        2
      </span>
      <div className="mt-2 w-px h-full md:mt-0 md:ms-2 md:w-full md:h-px md:flex-1 bg-gray-200 group-last:hidden dark:bg-neutral-700"></div>
    </div>
    <div className="grow md:grow-0 md:mt-3 pb-5">
      <span className="block text-sm font-medium text-gray-800 dark:text-white">
        Step
      </span>
      <p className="text-sm text-gray-500 dark:text-neutral-500">
        This is a description text.
      </p>
    </div>
  </li>

  <li className="md:shrink md:basis-0 flex-1 group flex gap-x-2 md:block">
    <div className="min-w-7 min-h-7 flex flex-col items-center md:w-full md:inline-flex md:flex-wrap md:flex-row text-xs align-middle">
      <span className="size-7 flex justify-center items-center shrink-0 bg-gray-100 font-medium text-gray-800 rounded-full dark:bg-neutral-700 dark:text-white">
        3
      </span>
      <div className="mt-2 w-px h-full md:mt-0 md:ms-2 md:w-full md:h-px md:flex-1 bg-gray-200 group-last:hidden dark:bg-neutral-700"></div>
    </div>
    <div className="grow md:grow-0 md:mt-3 pb-5">
      <span className="block text-sm font-medium text-gray-800 dark:text-white">
        Step
      </span>
      <p className="text-sm text-gray-500 dark:text-neutral-500">
        This is a description text.
      </p>
    </div>
  </li>

</ul>

  )
}

export default Stepper
