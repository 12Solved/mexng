interface IconProps {
  size?: number;
  className?: string;
}

export default function CheckIcon({ size = 13, className = '' }: IconProps) {
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
      <path d="M3 8l3.5 3.5L13 4" />
    </svg>
  );
}