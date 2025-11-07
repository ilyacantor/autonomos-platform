import HeroSection from './HeroSection';
import AutonomOSArchitectureFlow from './AutonomOSArchitectureFlow';
import DemoScanPanel from './DemoScanPanel';

export default function ControlCenterPage() {
  return (
    <div className="space-y-8">
      <HeroSection />
      <DemoScanPanel />
      <AutonomOSArchitectureFlow />
    </div>
  );
}
