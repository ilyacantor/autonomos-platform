import { useEffect, useState } from 'react';

interface LaserPointerProps {
  /** Target position as percentage of container (0-100) */
  x: number;
  y: number;
  /** Optional label shown next to the dot */
  label?: string;
  /** Whether the pointer is visible */
  visible: boolean;
}

/**
 * Shell-owned laser pointer overlay — a white pulsing dot that highlights
 * where the user should click. Positioned via percentage coordinates
 * relative to the parent container (the iframe area).
 */
export default function LaserPointer({ x, y, label, visible }: LaserPointerProps) {
  const [show, setShow] = useState(false);

  // Slight delay before appearing so it doesn't flash during step transitions
  useEffect(() => {
    if (!visible) {
      setShow(false);
      return;
    }
    const timer = setTimeout(() => setShow(true), 400);
    return () => clearTimeout(timer);
  }, [visible, x, y]);

  if (!show) return null;

  return (
    <div
      className="absolute z-40 pointer-events-none"
      style={{
        left: `${x}%`,
        top: `${y}%`,
        transform: 'translate(-50%, -50%)',
      }}
    >
      {/* Outer pulse ring */}
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="w-10 h-10 rounded-full bg-white/10 animate-ping" />
      </div>

      {/* Middle glow */}
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="w-6 h-6 rounded-full bg-white/20 blur-sm" />
      </div>

      {/* Core dot */}
      <div className="relative flex items-center justify-center w-4 h-4">
        <div className="w-3 h-3 rounded-full bg-white shadow-[0_0_12px_4px_rgba(255,255,255,0.5)]" />
      </div>

      {/* Label */}
      {label && (
        <div
          className="absolute left-6 top-1/2 -translate-y-1/2 whitespace-nowrap bg-gray-900/90 border border-gray-700 text-gray-200 text-xs font-medium px-2.5 py-1.5 rounded-md shadow-lg"
        >
          <span className="text-cyan-400 mr-1">&#x25B6;</span>
          {label}
        </div>
      )}
    </div>
  );
}
