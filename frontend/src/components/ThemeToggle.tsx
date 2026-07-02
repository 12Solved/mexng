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

import { MoonIcon, SunIcon } from '../assets/icons';
