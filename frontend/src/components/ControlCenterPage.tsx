import AutonomOSArchitectureFlow from './AutonomOSArchitectureFlow';
import DemoScanPanel from './DemoScanPanel';
import NLPGateway from './NLPGateway';

export default function ControlCenterPage() {
  return (
    <div className="space-y-8">
      <NLPGateway />
      <DemoScanPanel />
      <AutonomOSArchitectureFlow />
    </div>
  );
}
