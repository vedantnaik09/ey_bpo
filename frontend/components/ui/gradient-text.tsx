"use client";

interface GradientTextProps {
  children: React.ReactNode;
  className?: string;
}

export function GradientText({ children, className = "" }: GradientTextProps) {
  return (
    <span
      className={`bg-gradient-to-r from-purple-600 via-indigo-600 via-pink-600 to-purple-600 bg-clip-text text-transparent animate-gradient ${className}`}
      style={{
        backgroundSize: "200% 200%",
        animation: "gradientAnimation 3s ease infinite",
      }}
    >
      {children}
    </span>
  );
}
