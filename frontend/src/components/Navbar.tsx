import { useState, useEffect } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { Dialog, DialogBackdrop, DialogPanel } from '@headlessui/react'
import ThemeToggle from './ThemeToggle'
import { useUser } from '../context/UserContext.tsx'
import { UserIcon } from '../assets/icons'

const NAV_LINKS = [
  { to: '/', label: 'Dashboard', exact: true },
  { to: '/emails', label: 'Emails', exact: false },
  { to: '/logs', label: 'Logs', exact: false },
  { to: '/workflow', label: 'Workflows', exact: false },
  { to: '/checkpoints', label: 'Checkpoints', exact: false },
]



export default function Navbar() {
  const [open, setOpen] = useState(false)
  const [dark, setDark] = useState(() => {
    const saved = localStorage.getItem('theme')
    return saved ? saved === 'dark' : true
  })
  const location = useLocation()
  const { user } = useUser()

  useEffect(() => setOpen(false), [location.pathname])

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
    localStorage.setItem('theme', dark ? 'dark' : 'light')
  }, [dark])

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
      isActive
        ? 'bg-slate-700 text-white dark:bg-slate-700 dark:text-white'
        : 'text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800'
    }`

  const mobileLinkClass = ({ isActive }: { isActive: boolean }) =>
    `px-4 py-3 rounded-lg text-sm font-medium transition-colors ${
      isActive
        ? 'bg-slate-700 text-white dark:bg-slate-700 dark:text-white'
        : 'text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800'
    }`

  return (
    <>
      <nav className="flex items-center justify-between px-5 h-14 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800">

        <div className="hidden sm:flex items-center gap-1">
          {NAV_LINKS.map(({ to, label, exact }) => (
            <NavLink key={to} to={to} end={exact} className={linkClass}>
              {label}
            </NavLink>
          ))}
        </div>

        <div className="flex items-center gap-3">
          {user && (
            <span
              title={user.email ?? undefined}
              className="hidden sm:flex items-center gap-1.5 text-sm text-slate-500 dark:text-slate-400"
            >
              <UserIcon size={16} />
              {user.name}
            </span>
          )}
          <ThemeToggle />
          <button
            onClick={() => setOpen(true)}
            className="sm:hidden flex flex-col gap-1.5 p-2"
            aria-label="Open menu"
          >
            <span className="block w-5 h-px bg-slate-600 dark:bg-gray-300" />
            <span className="block w-5 h-px bg-slate-600 dark:bg-gray-300" />
            <span className="block w-5 h-px bg-slate-600 dark:bg-gray-300" />
          </button>
        </div>
      </nav>

      <Dialog open={open} onClose={setOpen} className="relative z-50 sm:hidden">
        <DialogBackdrop
          transition
          className="fixed inset-0 bg-black/50 transition-opacity duration-300 ease-in-out data-closed:opacity-0"
        />
        <div className="fixed inset-0 overflow-hidden">
          <div className="absolute inset-0 overflow-hidden">
            <div className="pointer-events-none fixed inset-y-0 right-0 flex max-w-full">
              <DialogPanel
                transition
                className="pointer-events-auto w-64 transform transition duration-300 ease-in-out data-closed:translate-x-full"
              >
                <div className="flex h-full flex-col bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-slate-800 py-6 shadow-xl">
                  <div className="px-6 mb-4">
                    <p className="text-xs font-semibold uppercase tracking-widest text-slate-400">Menu</p>
                  </div>
                  <nav className="flex flex-col gap-1 px-3 flex-1 min-h-0 overflow-y-auto">
                    {NAV_LINKS.map(({ to, label, exact }) => (
                      <NavLink key={to} to={to} end={exact} className={mobileLinkClass}>
                        {label}
                      </NavLink>
                    ))}
                  </nav>
                  <div className="mt-auto px-3 pt-4 border-t border-slate-200 dark:border-slate-800">
                    {user && (
                      <p className="px-4 pb-2 flex items-center gap-1.5 text-sm text-slate-500 dark:text-slate-400">
                        <UserIcon size={16} />
                        {user.name}
                      </p>
                    )}
                    <p className="px-4 pb-2 text-xs font-semibold uppercase tracking-widest text-slate-400">Appearance</p>
                    <div className="flex justify-start px-1">
                      <ThemeToggle />
                    </div>
                  </div>
                </div>
              </DialogPanel>
            </div>
          </div>
        </div>
      </Dialog>
    </>
  )
}