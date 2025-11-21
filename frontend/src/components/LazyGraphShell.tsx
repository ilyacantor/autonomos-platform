import LiveSankeyGraph from './LiveSankeyGraph';

// FIX: LazyGraphShell converted to simple wrapper
// IntersectionObserver removed - graph activates immediately on mount
// This prevents LazyGraphShell from blocking initial state fetch
export default function LazyGraphShell() {
  return (
    <div className="w-full">
      <LiveSankeyGraph />
    </div>
  );
}
