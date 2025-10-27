import { useState, useEffect } from 'react';
import { CheckCircle, AlertCircle, Info, Activity } from 'lucide-react';

interface DataSource {
  id: string;
  name: string;
  angle: number;
  logo: string;
}

interface ConnectionLog {
  time: string;
  type: 'success' | 'warning' | 'info' | 'healing';
  message: string;
  source?: string;
}

const dataSources: DataSource[] = [
  { id: 'salesforce', name: 'Salesforce', angle: 0, logo: '/assets/logos/salesforce_1761580451810.png' },
  { id: 'sap', name: 'SAP', angle: 45, logo: '/assets/logos/sap_1761580451810.png' },
  { id: 'mongodb', name: 'MongoDB', angle: 90, logo: '/assets/logos/mongodb_1761580451811.png' },
  { id: 'snowflake', name: 'Snowflake', angle: 135, logo: '/assets/logos/snowflake_1761580451810.png' },
  { id: 'dynamics', name: 'Dynamics', angle: 180, logo: '/assets/logos/dynamics_1761580451812.png' },
  { id: 'netsuite', name: 'NetSuite', angle: 225, logo: '/assets/logos/Netsuite_1761580451811.png' },
  { id: 'hubspot', name: 'HubSpot', angle: 270, logo: '/assets/logos/hubspot_1761580451812.png' },
  { id: 'supabase', name: 'Supabase', angle: 315, logo: '/assets/logos/supabase_1761580451809.png' },
];

export default function AAMContainer() {
  const [healingSource, setHealingSource] = useState<string | null>(null);
  const [healingPhase, setHealingPhase] = useState<'normal' | 'drift' | 'healing' | 'restored'>('normal');
  const [logs, setLogs] = useState<ConnectionLog[]>([
    { time: '17:07:43', type: 'success', message: 'All systems healthy', source: 'system' },
  ]);
  const [cycleCount, setCycleCount] = useState(0);

  // Self-healing animation cycle
  useEffect(() => {
    const cycle = async () => {
      await new Promise(resolve => setTimeout(resolve, 4000));
      
      const randomSource = dataSources[Math.floor(Math.random() * dataSources.length)];
      setHealingSource(randomSource.id);
      
      setHealingPhase('drift');
      const driftTime = new Date().toLocaleTimeString('en-US', { hour12: false });
      setLogs(prev => [
        { time: driftTime, type: 'warning', message: `${randomSource.name} schema drift detected...`, source: randomSource.id },
        ...prev.slice(0, 19)
      ]);
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      setHealingPhase('healing');
      const healTime = new Date().toLocaleTimeString('en-US', { hour12: false });
      setLogs(prev => [
        { time: healTime, type: 'healing', message: `Autonomous remapping initiated for ${randomSource.name}...`, source: randomSource.id },
        ...prev.slice(0, 19)
      ]);
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      setHealingPhase('restored');
      const restoreTime = new Date().toLocaleTimeString('en-US', { hour12: false });
      setLogs(prev => [
        { time: restoreTime, type: 'success', message: `${randomSource.name} connection restored ✓`, source: randomSource.id },
        ...prev.slice(0, 19)
      ]);
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      setHealingPhase('normal');
      setHealingSource(null);
      setCycleCount(c => c + 1);
    };

    cycle();
    const interval = setInterval(cycle, 9000);
    return () => clearInterval(interval);
  }, [cycleCount]);

  return (
    <div className="bg-black border-t border-b border-cyan-500/30 py-12 -mx-6 px-6 relative overflow-hidden">
      {/* Subtle Mesh Background */}
      <div 
        className="absolute inset-0 opacity-10 pointer-events-none"
        style={{
          backgroundImage: `
            linear-gradient(rgba(6, 182, 212, 0.3) 1px, transparent 1px),
            linear-gradient(90deg, rgba(6, 182, 212, 0.3) 1px, transparent 1px)
          `,
          backgroundSize: '40px 40px',
        }}
      />

      {/* Content */}
      <div className="relative z-10">
        {/* Title */}
        <div className="mb-8">
          <h2 className="text-3xl font-medium text-cyan-400">Adaptive API Mesh (AAM)</h2>
          <p className="text-lg text-slate-400 mt-2">Self-healing integration gateway with autonomous drift repair</p>
        </div>

        {/* Layered Stack Visualization (HubSpot style) */}
        <div className="relative mb-12 flex items-center justify-center min-h-[400px] py-12">
          {/* Isometric layered cards container */}
          <div className="relative w-full max-w-6xl h-[350px]" style={{ perspective: '1500px', transformStyle: 'preserve-3d' }}>
            
            {/* Layer 1: Execution Plane (back/left) */}
            <div 
              className="absolute w-[420px] h-[320px] rounded-xl shadow-2xl"
              style={{
                left: '5%',
                top: '50%',
                transform: 'translateY(-50%) rotateY(-8deg)',
                background: 'linear-gradient(135deg, #1e3a8a 0%, #1e293b 100%)',
                border: '1px solid rgba(71, 85, 105, 0.5)',
              }}
            >
              <div className="p-8 h-full flex flex-col justify-between relative">
                <div className="absolute inset-0 bg-gradient-to-br from-slate-700/20 to-transparent rounded-xl"></div>
                {/* Text remains flat - no transform */}
                <div className="relative z-10">
                  <div className="text-slate-400 text-xs font-medium uppercase tracking-wider mb-2">Layer 1</div>
                  <h3 className="text-2xl font-medium text-slate-100 mb-1">Execution Plane</h3>
                  <p className="text-sm text-slate-400 mb-4">Adopted Infrastructure</p>
                  <div className="space-y-2 text-sm text-slate-300">
                    <div className="flex items-center gap-2">
                      <div className="w-1.5 h-1.5 bg-slate-400 rounded-full"></div>
                      <span>Universal Connectivity</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-1.5 h-1.5 bg-slate-400 rounded-full"></div>
                      <span>API Gateway & Security</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-1.5 h-1.5 bg-slate-400 rounded-full"></div>
                      <span>Data Synchronization</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Layer 2: Adaptive Intelligence Plane (middle/center) - CENTERPIECE */}
            <div 
              className="absolute w-[420px] h-[320px] rounded-xl shadow-2xl"
              style={{
                left: '50%',
                top: '50%',
                transform: 'translate(-50%, -50%) rotateY(0deg)',
                background: 'linear-gradient(135deg, #0ea5e9 0%, #06b6d4 50%, #0891b2 100%)',
                border: '2px solid rgba(6, 182, 212, 0.8)',
                boxShadow: '0 0 40px rgba(6, 182, 212, 0.5), 0 20px 60px rgba(0, 0, 0, 0.5)',
                zIndex: 10,
              }}
            >
              <div className="p-8 h-full flex flex-col justify-between relative overflow-hidden rounded-xl">
                {/* Inner glow effect */}
                <div className="absolute inset-0 bg-gradient-to-br from-white/20 to-transparent"></div>
                <div className="absolute inset-0 bg-gradient-to-tl from-cyan-300/10 to-transparent"></div>
                
                {/* Text remains flat - no transform */}
                <div className="relative z-10">
                  <div className="text-cyan-100 text-xs font-medium uppercase tracking-wider mb-2">Layer 2 • Core IP</div>
                  <h3 className="text-2xl font-medium text-white mb-1">Adaptive Intelligence Plane</h3>
                  <p className="text-sm text-cyan-50 mb-4">Self-Healing Core ⚡</p>
                  <div className="space-y-2 text-sm text-white">
                    <div className="flex items-center gap-2">
                      <div className="w-1.5 h-1.5 bg-white rounded-full animate-pulse"></div>
                      <span>RAG Engine (Autonomous Repair)</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-1.5 h-1.5 bg-white rounded-full animate-pulse"></div>
                      <span>Real-time Schema Observation</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-1.5 h-1.5 bg-white rounded-full animate-pulse"></div>
                      <span>Drift Detection</span>
                    </div>
                  </div>
                </div>

                {/* Floating words animation */}
                <div className="absolute right-6 top-12 bottom-12 w-32 overflow-hidden pointer-events-none">
                  {['API Gateway', 'OAuth', 'Connector', 'Endpoint', 'Normalization', 'Schema', 'Trigger', 'Action', 'Batch Sync'].map((word, i) => (
                    <div
                      key={`float-word-${i}`}
                      className="absolute right-0 text-white/60 text-[10px] font-medium whitespace-nowrap"
                      style={{
                        animation: `floatUp 5s linear ${i * 0.5}s infinite`,
                      }}
                    >
                      {word}
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Layer 3: Control Plane (front/right) */}
            <div 
              className="absolute w-[420px] h-[320px] rounded-xl shadow-2xl backdrop-blur-md"
              style={{
                right: '5%',
                top: '50%',
                transform: 'translateY(-50%) rotateY(8deg)',
                background: 'linear-gradient(135deg, rgba(148, 163, 184, 0.3) 0%, rgba(203, 213, 225, 0.2) 100%)',
                border: '1px solid rgba(148, 163, 184, 0.5)',
                backdropFilter: 'blur(12px)',
              }}
            >
              <div className="p-8 h-full flex flex-col justify-between relative">
                <div className="absolute inset-0 bg-gradient-to-br from-white/10 to-transparent rounded-xl"></div>
                {/* Text remains flat - no transform */}
                <div className="relative z-10">
                  <div className="text-slate-300 text-xs font-medium uppercase tracking-wider mb-2">Layer 3</div>
                  <h3 className="text-2xl font-medium text-slate-100 mb-1">Control Plane</h3>
                  <p className="text-sm text-slate-300 mb-4">Governance & Monitoring</p>
                  <div className="space-y-2 text-sm text-slate-200">
                    <div className="flex items-center gap-2">
                      <div className="w-1.5 h-1.5 bg-slate-300 rounded-full"></div>
                      <span>AOS Control Center</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-1.5 h-1.5 bg-slate-300 rounded-full"></div>
                      <span>Real-time Alerting</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-1.5 h-1.5 bg-slate-300 rounded-full"></div>
                      <span>Human-in-the-Loop (HITL)</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Connection Log & Description */}
        <div className="grid grid-cols-1 lg:grid-cols-[450px_1fr] gap-8 max-w-6xl mx-auto mt-16">
          {/* Left: Connection Log */}
          <div className="bg-slate-900/80 rounded-lg border border-slate-700/50 p-4">
            <div className="flex items-center gap-2 mb-3">
              <Activity className="w-4 h-4 text-cyan-400" />
              <h3 className="text-sm font-medium text-slate-200">Real-time Connection Monitor</h3>
              <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
            </div>
            
            <div className="bg-slate-950/60 rounded-md border border-slate-700/30 p-3 max-h-[280px] overflow-y-auto">
              <div className="space-y-2 font-mono text-xs">
                {logs.map((log, index) => (
                  <div key={index} className="flex items-start gap-2 pb-2 border-b border-slate-700/20 last:border-0">
                    <span className="text-slate-500 flex-shrink-0">{log.time}</span>
                    {log.type === 'success' && (
                      <CheckCircle className="w-3 h-3 text-green-400 flex-shrink-0 mt-0.5" />
                    )}
                    {log.type === 'warning' && (
                      <AlertCircle className="w-3 h-3 text-red-400 flex-shrink-0 mt-0.5" />
                    )}
                    {log.type === 'healing' && (
                      <Activity className="w-3 h-3 text-amber-400 flex-shrink-0 mt-0.5 animate-pulse" />
                    )}
                    {log.type === 'info' && (
                      <Info className="w-3 h-3 text-blue-400 flex-shrink-0 mt-0.5" />
                    )}
                    <span className={`leading-tight flex-1 ${
                      log.type === 'warning' ? 'text-red-300' : 
                      log.type === 'healing' ? 'text-amber-300' : 
                      log.type === 'success' ? 'text-green-300' : 
                      'text-slate-300'
                    }`}>{log.message}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Right: Description */}
          <div className="flex flex-col justify-center gap-6">
            <div>
              <h3 className="text-xl font-medium text-cyan-400 mb-3">Three-Layer Architecture</h3>
              <p className="text-lg text-slate-300 leading-relaxed">
                The AAM is built on a robust foundation (Execution), powered by proprietary self-healing 
                intelligence (Adaptive Intelligence), and managed through a unified control interface (AOS Control Center).
              </p>
            </div>
            
            <div>
              <h3 className="text-xl font-medium text-cyan-400 mb-3">Self-Healing Intelligence</h3>
              <p className="text-lg text-slate-300 leading-relaxed">
                The centerpiece Adaptive Intelligence layer continuously monitors, detects drift, 
                and autonomously repairs connections—ensuring zero-downtime resilience.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* CSS for floating words animation */}
      <style>{`
        @keyframes floatUp {
          0% {
            transform: translateY(250px);
            opacity: 0;
          }
          10% {
            opacity: 1;
          }
          90% {
            opacity: 1;
          }
          100% {
            transform: translateY(-50px);
            opacity: 0;
          }
        }
      `}</style>
    </div>
  );
}
