import { useSyncExternalStore } from 'react';

function subscribe(callback: () => void): () => void {
  const mo = new MutationObserver(callback);
  mo.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['class'],
  });
  return () => mo.disconnect();
}

function getSnapshot(): boolean {
  return document.documentElement.classList.contains('dark');
}

function getServerSnapshot(): boolean {
  return false;
}

export function useHtmlDarkClass(): boolean {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}
