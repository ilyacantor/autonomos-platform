import MermaidGallery from './MermaidGallery';

export default function DiagramsPage() {
  return (
    <main className="min-h-screen" style={{ background: "#0b0f14", color: "#e6edf3" }}>
      <div className="px-6 pt-8 pb-12">
        <div className="max-w-6xl mx-auto mb-8">
          <h1 className="text-3xl font-bold mb-3 bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
            AutonomOS – Live Architecture Diagrams
          </h1>
          <p className="text-gray-400 text-lg mb-2">
            Rendered automatically from <code className="bg-gray-800 px-2 py-1 rounded text-sm text-blue-300">/public/diagrams.md</code>
          </p>
          <p className="text-sm text-gray-500">
            All diagrams update in real-time as you edit the source file. No rebuild required.
          </p>
        </div>
        <MermaidGallery src="/diagrams.md" />
      </div>
    </main>
  );
}
