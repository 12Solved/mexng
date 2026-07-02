interface IconProps {
  size?: number;
  className?: string;
}

export default function DownloadIcon({ size = 13, className = '' }: IconProps) {
  return (
    <svg 
      width={size} 
      height={size} 
      viewBox="0 0 16 16" 
      fill="none" 
      stroke="currentColor" 
      strokeWidth="1.5" 
      strokeLinecap="round" 
      strokeLinejoin="round"
      className={className}
    >
      <path d="M8 2v8M5 7l3 3 3-3M2 12h12" />
    </svg>
  );
}