interface IconProps {
  size?: number;
  className?: string;
}

export default function WorkflowIcon({ size = 16, className = '' }: IconProps) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <rect x="3" y="3" width="8" height="6" rx="1.5" />
      <rect x="13" y="15" width="8" height="6" rx="1.5" />
      <path d="M7 9v2.5a1.5 1.5 0 001.5 1.5h7a1.5 1.5 0 011.5 1.5V15" />
    </svg>
  );
}
