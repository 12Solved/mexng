export default function SpinnerIcon() {
  return (
    <svg className="spinner" width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
      <path d="M8 1.5A6.5 6.5 0 1 1 1.5 8" />
      <style>{`.spinner { animation: spin 0.75s linear infinite; transform-origin: center; } @keyframes spin { to { transform: rotate(360deg) } }`}</style>
    </svg>
  )
}