import { Dialog, DialogBackdrop, DialogPanel, DialogTitle, TransitionChild } from '@headlessui/react'
import type { Email } from '../types/email'

interface DrawerProps {
  open: boolean
  onClose: () => void
  email: Email | null
}

export default function EmailDrawer({ open, onClose, email }: DrawerProps) {


  return (
    <div>
      <Dialog open={open} onClose={onClose} className="relative z-10">
        <DialogBackdrop
          transition
          className="fixed inset-0 bg-gray-900/50 transition-opacity duration-500 ease-in-out data-closed:opacity-0"
        />

        <div className="fixed inset-0 overflow-hidden">
          <div className="absolute inset-0 overflow-hidden">
            <div className="pointer-events-none fixed inset-y-0 right-0 flex max-w-full pl-10 sm:pl-16">
              <DialogPanel
                transition
                className="pointer-events-auto relative w-screen max-w-2xl transform transition duration-500 ease-in-out data-closed:translate-x-full sm:duration-700"
              >
                <TransitionChild>
                  <div className="absolute top-0 left-0 -ml-8 flex pt-4 pr-2 duration-500 ease-in-out data-closed:opacity-0 sm:-ml-10 sm:pr-4">
                  </div>
                </TransitionChild>
                <div className="relative flex h-full flex-col overflow-y-auto bg-gray-800 py-6 shadow-xl after:absolute after:inset-y-0 after:left-0 after:w-px after:bg-white/10">
                  <div className="px-4 sm:px-6">
                    <DialogTitle className="text-base font-semibold text-white">{email?.subject}</DialogTitle>
                  </div>
                  <div className="relative mt-6 flex-1 px-4 sm:px-6">
                    <div className='flex gap-3'>
                        <div className='flex-1 flex flex-col font-medium items-center uppercase px-4 py-2 rounded-lg border border-green-200 bg-green-50'>
                          <span className='text-lg font-medium text-green-700'>{email?.run_summary.success}</span>
                          <span className='text-xs text-green-600'>Success</span>
                        </div>
                        <div className='flex-1 flex flex-col font-medium items-center uppercase px-4 py-2 rounded-lg border border-yellow-200 bg-yellow-50'>
                          <span className='text-lg font-medium text-yellow-700'>{email?.run_summary.skipped}</span>
                          <span className='text-xs text-yellow-600'>Skipped</span>
                        </div>
                        <div className='flex-1 flex flex-col font-medium items-center uppercase px-4 py-2 rounded-lg border border-red-200 bg-red-50'>
                          <span className='text-lg font-medium text-red-700'>{email?.run_summary.failed}</span>
                          <span className='text-xs text-red-600'>Failed</span>
                        </div>
                    </div>
                  </div>
                </div>
              </DialogPanel>
            </div>
          </div>
        </div>
      </Dialog>
    </div>
  )
}