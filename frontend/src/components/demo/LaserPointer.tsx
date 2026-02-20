interface LaserPointerProps {
  /** Target position as percentage of container (0-100) */
  x: number;
  y: number;
  /** Optional label shown next to the dot */
  label?: string;
  /** Whether the pointer is visible */
  visible: boolean;
}

export default function LaserPointer({ x, y, label, visible }: LaserPointerProps) {
  if (!visible) return null;

  return (
    <div
      style={{
        position: 'absolute',
        left: `${x}%`,
        top: `${y}%`,
        transform: 'translate(-50%, -50%)',
        zIndex: 45,
        pointerEvents: 'none',
      }}
    >
      {/* Outer pulse ring — CSS animation inline to avoid Tailwind purge issues */}
      <div
        style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          width: 40,
          height: 40,
          marginTop: -20,
          marginLeft: -20,
          borderRadius: '50%',
          backgroundColor: 'rgba(255,255,255,0.15)',
          animation: 'laser-ping 1.5s cubic-bezier(0,0,0.2,1) infinite',
        }}
      />

      {/* Middle glow */}
      <div
        style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          width: 24,
          height: 24,
          marginTop: -12,
          marginLeft: -12,
          borderRadius: '50%',
          backgroundColor: 'rgba(255,255,255,0.25)',
          filter: 'blur(4px)',
        }}
      />

      {/* Core dot */}
      <div
        style={{
          position: 'relative',
          width: 14,
          height: 14,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <div
          style={{
            width: 12,
            height: 12,
            borderRadius: '50%',
            backgroundColor: '#ffffff',
            boxShadow: '0 0 16px 6px rgba(255,255,255,0.6), 0 0 40px 12px rgba(255,255,255,0.25)',
          }}
        />
      </div>

      {/* Label */}
      {label && (
        <div
          style={{
            position: 'absolute',
            left: 24,
            top: '50%',
            transform: 'translateY(-50%)',
            whiteSpace: 'nowrap',
            backgroundColor: 'rgba(17,24,39,0.95)',
            border: '1px solid rgba(75,85,99,0.7)',
            color: '#e5e7eb',
            fontSize: 12,
            fontWeight: 500,
            padding: '6px 10px',
            borderRadius: 6,
            boxShadow: '0 4px 12px rgba(0,0,0,0.4)',
          }}
        >
          <span style={{ color: '#22d3ee', marginRight: 4 }}>&#9654;</span>
          {label}
        </div>
      )}

      {/* Keyframe animation injected via style tag */}
      <style>{`
        @keyframes laser-ping {
          0% { transform: scale(1); opacity: 1; }
          75%, 100% { transform: scale(2.2); opacity: 0; }
        }
      `}</style>
    </div>
  );
}
