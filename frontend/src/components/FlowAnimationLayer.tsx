import { useRef, useEffect } from "react";

interface FlowLink {
  x0: number;
  y0: number;
  x1: number;
  y1: number;
  sourceLayer?: number;
  targetLayer?: number;
}

interface FlowAnimationLayerProps {
  links?: FlowLink[];
  isRunning?: boolean;
}

const FlowAnimationLayer = ({ links = [], isRunning = false }: FlowAnimationLayerProps) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const animRef = useRef<number | null>(null);
  const activeRef = useRef<boolean>(false);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const resize = () => {
      const parent = canvas.parentElement;
      if (!parent) return;
      const { width, height } = parent.getBoundingClientRect();
      canvas.width = width;
      canvas.height = height;
    };
    resize();
    window.addEventListener("resize", resize);

    let t = 0;
    const draw = () => {
      if (!ctx) return;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.lineWidth = 2;
      for (const l of links) {
        const isSource = (l.sourceLayer === 0 && l.targetLayer === 1);
        ctx.strokeStyle = isSource ? "rgba(0,255,136,0.9)" : "rgba(0,200,255,0.7)";
        const dashLen = 14, gap = 12;
        const phase = (t * 2) % (dashLen + gap);
        ctx.setLineDash([dashLen, gap]);
        ctx.lineDashOffset = -phase;
        ctx.beginPath();
        ctx.moveTo(l.x0, l.y0);
        ctx.lineTo(l.x1, l.y1);
        ctx.stroke();
      }
      if (activeRef.current) {
        t += 1;
        animRef.current = requestAnimationFrame(draw);
      }
    };

    const start = () => {
      if (!activeRef.current) {
        activeRef.current = true;
        t = 0;
        animRef.current = requestAnimationFrame(draw);
      }
    };
    const stop = () => {
      activeRef.current = false;
      if (animRef.current) cancelAnimationFrame(animRef.current);
      ctx.clearRect(0, 0, canvas.width, canvas.height);
    };

    if (isRunning) {
      start();
    } else {
      setTimeout(() => stop(), 2000);
    }

    return () => {
      stop();
      window.removeEventListener("resize", resize);
    };
  }, [links, isRunning]);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        width: "100%",
        height: "100%",
        pointerEvents: "none",
      }}
    />
  );
};

export default FlowAnimationLayer;
