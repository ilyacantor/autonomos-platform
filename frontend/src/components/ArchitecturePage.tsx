export default function ArchitecturePage() {
  return (
    <div className="h-full w-full -m-6">
      <iframe
        src="/architecture.html"
        className="w-full h-full border-0"
        title="AutonomOS Architecture Documentation"
        style={{ height: 'calc(100vh - 64px)' }}
      />
    </div>
  );
}
