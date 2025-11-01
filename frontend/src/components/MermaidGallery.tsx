import { useEffect, useMemo, useState } from "react";
import mermaid from "mermaid";

type Section = { title: string; code: string };

const extractMermaidSections = (md: string): Section[] => {
  const sections: Section[] = [];
  const codeRe = /```mermaid\s+?([\s\S]*?)```/g;
  let match: RegExpExecArray | null;
  while ((match = codeRe.exec(md))) {
    const start = match.index;
    const before = md.slice(0, start);
    const headingMatches = [...before.matchAll(/^(#{1,6})\s+(.*)$/gm)];
    const lastHeading = headingMatches.length
      ? headingMatches[headingMatches.length - 1][2].trim()
      : "Diagram";
    sections.push({ title: lastHeading, code: match[1].trim() });
  }
  return sections;
};

export default function MermaidGallery({ src = "/diagrams.md" }: { src?: string }) {
  const [raw, setRaw] = useState<string>("");

  useEffect(() => {
    let mounted = true;
    fetch(src, { cache: "no-store" })
      .then(r => r.text())
      .then(t => { if (mounted) setRaw(t); })
      .catch(err => console.error("Error loading diagrams:", err));
    return () => { mounted = false; };
  }, [src]);

  const sections = useMemo(() => extractMermaidSections(raw), [raw]);

  useEffect(() => {
    mermaid.initialize({
      startOnLoad: false,
      theme: "dark",
      securityLevel: "loose",
      fontFamily: "Inter, system-ui, Arial, sans-serif",
      sequence: { useMaxWidth: true, wrap: true },
      flowchart: { useMaxWidth: true, htmlLabels: true, curve: "basis" }
    });
    const id = requestAnimationFrame(() => {
      mermaid.init(undefined, document.querySelectorAll(".mermaid"));
    });
    return () => cancelAnimationFrame(id);
  }, [sections]);

  if (import.meta.hot) {
    import.meta.hot.on("vite:afterUpdate", () => {
      fetch(src + `?v=${Date.now()}`, { cache: "no-store" })
        .then(r => r.text())
        .then(setRaw)
        .catch(() => {});
    });
  }

  return (
    <div className="max-w-6xl mx-auto p-4 space-y-6">
      {sections.map((s, i) => (
        <section key={i} className="space-y-2 bg-gray-800/50 rounded-lg p-6 border border-gray-700">
          <h2 className="text-xl font-semibold text-blue-400">{i + 1}. {s.title}</h2>
          <pre className="mermaid bg-gray-900/30 p-4 rounded overflow-x-auto">{s.code}</pre>
        </section>
      ))}
      {!sections.length && (
        <p className="opacity-70 text-center text-gray-400">No Mermaid blocks found in {src}.</p>
      )}
    </div>
  );
}
