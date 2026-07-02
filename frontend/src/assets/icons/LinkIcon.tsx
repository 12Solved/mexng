interface IconProps {
  size?: number;
  className?: string;
}

export default function LinkIcon({ size = 10, className = '' }: IconProps) {
  return (
    <svg 
      xmlns="http://www.w3.org/2000/svg" 
      width={size} 
      height={size} 
      viewBox="0 0 12 12" 
      fill="none" 
      stroke="currentColor" 
      strokeWidth="1.8" 
      strokeLinecap="round" 
      strokeLinejoin="round"
      className={className}
    >
      <path d="M5 2H2a1 1 0 00-1 1v7a1 1 0 001 1h7a1 1 0 001-1V7" />
      <path d="M8 1h3v3" />
      <path d="M11 1L6 6" />
    </svg>
  );
}