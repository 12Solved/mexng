export type ThemeMode = 'light' | 'dark';

const STORAGE_KEY = 'theme';

export function setTheme(mode: ThemeMode): void {
  localStorage.setItem(STORAGE_KEY, mode);
  document.documentElement.classList.toggle('dark', mode === 'dark');
}

export function getTheme(): ThemeMode {
  return document.documentElement.classList.contains('dark') ? 'dark' : 'light';
}

export function toggleTheme(): ThemeMode {
  const next: ThemeMode = getTheme() === 'dark' ? 'light' : 'dark';
  setTheme(next);
  return next;
}
