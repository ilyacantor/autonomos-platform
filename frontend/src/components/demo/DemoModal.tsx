import { useState, useRef, useCallback, useEffect } from 'react';
import { X, GripHorizontal } from 'lucide-react';

interface DemoModalProps {
  title: string;
  children: React.ReactNode;
  onClose: () => void;
  visible: boolean;
}

export default function DemoModal({ title, children, onClose, visible }: DemoModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState({ x: 32, y: 32 });
  const [isDragging, setIsDragging] = useState(false);
  const dragOffset = useRef({ x: 0, y: 0 });

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (!modalRef.current) return;
    setIsDragging(true);
    dragOffset.current = {
      x: e.clientX - position.x,
      y: e.clientY - position.y,
    };
  }, [position]);

  useEffect(() => {
    if (!isDragging) return;

    const handleMouseMove = (e: MouseEvent) => {
      setPosition({
        x: e.clientX - dragOffset.current.x,
        y: e.clientY - dragOffset.current.y,
      });
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging]);

  // Reset position when modal becomes visible
  useEffect(() => {
    if (visible) {
      setPosition({ x: 32, y: 32 });
    }
  }, [visible]);

  if (!visible) return null;

  return (
    <div
      ref={modalRef}
      className="fixed z-50 bg-gray-900 border border-gray-700 rounded-lg shadow-2xl shadow-black/50"
      style={{
        left: position.x,
        top: position.y,
        maxWidth: 420,
        minWidth: 320,
      }}
    >
      {/* Drag handle */}
      <div
        onMouseDown={handleMouseDown}
        className={`flex items-center justify-between px-4 py-3 border-b border-gray-800 ${
          isDragging ? 'cursor-grabbing' : 'cursor-grab'
        } select-none`}
      >
        <div className="flex items-center gap-2">
          <GripHorizontal className="w-4 h-4 text-gray-600" />
          <span className="text-sm font-semibold text-gray-200">{title}</span>
        </div>
        <button
          onClick={onClose}
          className="p-1 hover:bg-gray-800 rounded transition-colors"
          title="Close (Esc)"
        >
          <X className="w-4 h-4 text-gray-500" />
        </button>
      </div>

      {/* Content */}
      <div className="p-4">
        {children}
      </div>
    </div>
  );
}
