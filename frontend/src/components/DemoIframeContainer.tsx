interface DemoIframeContainerProps {
  src: string;
  title: string;
  allow?: string;
  minHeight?: string;
}

export default function DemoIframeContainer({
  src,
  title,
  allow = 'fullscreen',
  minHeight = '400px'
}: DemoIframeContainerProps) {
  return (
    <div className="relative w-full h-full" style={{ minHeight }}>
      <iframe
        src={src}
        className="absolute inset-0 w-full h-full"
        title={title}
        allow={allow}
        style={{
          border: 'none',
          backgroundColor: '#1a1a1a'
        }}
      />
    </div>
  );
}
