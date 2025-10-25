import { useEffect } from 'react';

export default function LegacyDCLUI() {
  useEffect(() => {
    // Redirect to the legacy static UI
    window.location.href = '/static/index.html';
  }, []);

  return (
    <div className="w-full h-screen flex items-center justify-center bg-slate-950">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-cyan-500 mx-auto mb-4"></div>
        <p className="text-slate-400">Loading Legacy DCL UI...</p>
      </div>
    </div>
  );
}
