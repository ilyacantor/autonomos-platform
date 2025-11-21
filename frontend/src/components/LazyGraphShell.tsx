import { useEffect, useRef, useState } from 'react';
import { Loader2 } from 'lucide-react';
import LiveSankeyGraph from './LiveSankeyGraph';

export default function LazyGraphShell() {
  const [isGraphActive, setIsGraphActive] = useState(false);
  const observerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const currentRef = observerRef.current;
    if (!currentRef) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting && !isGraphActive) {
            console.log('[DCL Graph] Now visible, activating lazy load...');
            setIsGraphActive(true);
          }
        });
      },
      {
        root: null,
        rootMargin: '100px',
        threshold: 0.01
      }
    );

    observer.observe(currentRef);

    return () => {
      if (currentRef) {
        observer.unobserve(currentRef);
      }
      observer.disconnect();
    };
  }, [isGraphActive]);

  return (
    <div ref={observerRef} className="w-full min-h-[500px]">
      {isGraphActive ? (
        <LiveSankeyGraph />
      ) : (
        <div className="rounded-xl bg-gray-800/40 border border-gray-700 shadow-sm ring-1 ring-cyan-500/10 p-8 w-full h-[500px] flex items-center justify-center">
          <p className="text-sm text-gray-400">Scroll to view interactive graph...</p>
        </div>
      )}
    </div>
  );
}
