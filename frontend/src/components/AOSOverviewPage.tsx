import EmbeddedApp from './EmbeddedApp';

export default function AOSOverviewPage() {
  return (
    <div className="h-full flex flex-col bg-gradient-to-b from-gray-900 to-gray-950">
      <div className="flex-1 p-6">
        <EmbeddedApp
          url="https://discovery-demo-standalone-ilyacantor.replit.app"
          title="AOS Overview - Discovery Demo"
          className="h-full min-h-[600px]"
        />
      </div>
    </div>
  );
}
