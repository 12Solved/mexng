import { useSyncExternalStore } from 'react';
import { setTheme } from '../theme';

function subscribe(callback: () => void): () => void {
  const mo = new MutationObserver(callback);
  mo.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['class'],
  });
  window.addEventListener('storage', callback);
  return () => {
    mo.disconnect();
    window.removeEventListener('storage', callback);
  };
}

function snap(): boolean {
  return document.documentElement.classList.contains('dark');
}

export default function ThemeToggle() {
  const dark = useSyncExternalStore(subscribe, snap, () => false);

  return (
    <button
      type="button"
      onClick={() => setTheme(dark ? 'light' : 'dark')}
      className="p-2 rounded-md text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors border border-transparent hover:border-slate-200 dark:hover:border-slate-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400"
      title={dark ? 'Switch to light mode' : 'Switch to dark mode'}
      aria-label={dark ? 'Switch to light mode' : 'Switch to dark mode'}
    >
      {dark ? (
        <SunIcon />
      ) : (
        <MoonIcon />
      )}
    </button>
  );
}

function MoonIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" />
    </svg>
  );
}

function SunIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" />
    </svg>
  );
}
