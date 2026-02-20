interface DemoIframeContainerProps {
  src: string;
  title: string;
  allow?: string;
}

export default function DemoIframeContainer({
  src,
  title,
  allow = 'fullscreen',
}: DemoIframeContainerProps) {
  return (
    <iframe
      src={src}
      className="w-full h-full"
      title={title}
      allow={allow}
      loading="lazy"
      style={{
        border: 'none',
        backgroundColor: '#1a1a1a'
      }}
    />
  );
}
