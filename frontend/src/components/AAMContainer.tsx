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

  // Helper function to create wavy path between two points
  const createWavyPath = (x1: number, y1: number, x2: number, y2: number) => {
    const midX = (x1 + x2) / 2;
    const midY = (y1 + y2) / 2;
    const dx = x2 - x1;
    const dy = y2 - y1;
    const distance = Math.sqrt(dx * dx + dy * dy);
    const waveAmplitude = distance * 0.1;
    const perpX = -dy / distance;
    const perpY = dx / distance;
    const controlX = midX + perpX * waveAmplitude;
    const controlY = midY + perpY * waveAmplitude;
    
    return `M ${x1} ${y1} Q ${controlX} ${controlY}, ${x2} ${y2}`;
  };

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

        {/* Hub and Spoke Visualization */}
        <div className="relative mb-8">
          <svg 
            viewBox="0 0 800 500" 
            className="w-full max-w-4xl mx-auto"
          >
            <defs>
              {/* Glow filters for different states */}
              <filter id="glowNormal">
                <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
                <feMerge>
                  <feMergeNode in="coloredBlur"/>
                  <feMergeNode in="SourceGraphic"/>
                </feMerge>
              </filter>
              <filter id="glowDrift">
                <feGaussianBlur stdDeviation="5" result="coloredBlur"/>
                <feMerge>
                  <feMergeNode in="coloredBlur"/>
                  <feMergeNode in="SourceGraphic"/>
                </feMerge>
              </filter>
              <filter id="glowHealing">
                <feGaussianBlur stdDeviation="6" result="coloredBlur"/>
                <feMerge>
                  <feMergeNode in="coloredBlur"/>
                  <feMergeNode in="SourceGraphic"/>
                </feMerge>
              </filter>
              
              {/* Hexagon gradient */}
              <linearGradient id="hexagonGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stopColor="#0e7490" />
                <stop offset="100%" stopColor="#164e63" />
              </linearGradient>
            </defs>

            {/* Wavy Connection Lines */}
            {dataSources.map((source) => {
              const radius = 180;
              const centerX = 400;
              const centerY = 250;
              const angleRad = (source.angle - 90) * (Math.PI / 180);
              const x = centerX + radius * Math.cos(angleRad);
              const y = centerY + radius * Math.sin(angleRad);
              
              const isHealing = healingSource === source.id;
              let strokeColor = '#06b6d4';
              let strokeWidth = 2;
              let opacity = 0.6;
              let filter = 'url(#glowNormal)';
              
              if (isHealing) {
                if (healingPhase === 'drift') {
                  strokeColor = '#ef4444';
                  strokeWidth = 3;
                  opacity = 1;
                  filter = 'url(#glowDrift)';
                } else if (healingPhase === 'healing') {
                  strokeColor = '#f59e0b';
                  strokeWidth = 3;
                  opacity = 1;
                  filter = 'url(#glowHealing)';
                } else if (healingPhase === 'restored') {
                  strokeColor = '#22c55e';
                  strokeWidth = 3;
                  opacity = 1;
                  filter = 'url(#glowDrift)';
                }
              }

              const pathD = createWavyPath(centerX, centerY, x, y);

              return (
                <g key={source.id}>
                  <path
                    d={pathD}
                    stroke={strokeColor}
                    strokeWidth={strokeWidth}
                    opacity={opacity}
                    fill="none"
                    filter={filter}
                    className="transition-all duration-500"
                  >
                    {!isHealing && (
                      <animate
                        attributeName="opacity"
                        values="0.6;0.9;0.6"
                        dur="3s"
                        repeatCount="indefinite"
                      />
                    )}
                  </path>
                  
                  {/* Pulse animation for healing */}
                  {isHealing && healingPhase === 'healing' && (
                    <path
                      d={pathD}
                      stroke={strokeColor}
                      strokeWidth={strokeWidth + 2}
                      opacity={0.3}
                      fill="none"
                    >
                      <animate
                        attributeName="opacity"
                        values="0;0.6;0"
                        dur="1s"
                        repeatCount="indefinite"
                      />
                    </path>
                  )}
                </g>
              );
            })}

            {/* Central AAM Core - Glowing Hexagon */}
            <g>
              {/* Outer glow rings */}
              <circle
                cx="400"
                cy="250"
                r="50"
                fill="none"
                stroke="#06b6d4"
                strokeWidth="1"
                opacity="0.2"
              >
                <animate
                  attributeName="r"
                  values="50;60;50"
                  dur="3s"
                  repeatCount="indefinite"
                />
                <animate
                  attributeName="opacity"
                  values="0.2;0.4;0.2"
                  dur="3s"
                  repeatCount="indefinite"
                />
              </circle>
              
              {/* Hexagon */}
              <polygon
                points="400,210 430,225 430,265 400,280 370,265 370,225"
                fill="url(#hexagonGradient)"
                stroke="#06b6d4"
                strokeWidth="2"
                filter="url(#glowNormal)"
              />
              
              {/* Inner glow */}
              <circle
                cx="400"
                cy="245"
                r="20"
                fill="#06b6d4"
                opacity="0.3"
              >
                <animate
                  attributeName="opacity"
                  values="0.3;0.6;0.3"
                  dur="2s"
                  repeatCount="indefinite"
                />
              </circle>
              
              {/* AAM text only */}
              <text
                x="400"
                y="253"
                textAnchor="middle"
                fill="white"
                fontSize="20"
                fontWeight="600"
              >
                AAM
              </text>
            </g>

            {/* Data Source Logos */}
            {dataSources.map((source) => {
              const radius = 180;
              const centerX = 400;
              const centerY = 250;
              const angleRad = (source.angle - 90) * (Math.PI / 180);
              const x = centerX + radius * Math.cos(angleRad);
              const y = centerY + radius * Math.sin(angleRad);
              
              const logoSize = 40;

              return (
                <g key={`logo-${source.id}`}>
                  {/* Logo background circle for contrast */}
                  <circle
                    cx={x}
                    cy={y}
                    r={logoSize / 2 + 4}
                    fill="rgba(15, 23, 42, 0.9)"
                    stroke="#334155"
                    strokeWidth="1"
                  />
                  
                  {/* Logo image */}
                  <image
                    href={source.logo}
                    x={x - logoSize / 2}
                    y={y - logoSize / 2}
                    width={logoSize}
                    height={logoSize}
                    className="transition-all duration-500"
                  />
                </g>
              );
            })}
          </svg>
        </div>

        {/* Connection Log & Description */}
        <div className="grid grid-cols-1 lg:grid-cols-[450px_1fr] gap-8 max-w-6xl mx-auto">
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
              <h3 className="text-xl font-medium text-cyan-400 mb-3">Universal Gateway</h3>
              <p className="text-lg text-slate-300 leading-relaxed">
                The AAM serves as a centralized integration hub connecting SaaS platforms, databases, 
                legacy systems, and APIs through a unified mesh architecture.
              </p>
            </div>
            
            <div>
              <h3 className="text-xl font-medium text-cyan-400 mb-3">Self-Healing Intelligence</h3>
              <p className="text-lg text-slate-300 leading-relaxed">
                Automatically detects schema drift, API changes, and connectivity issues. 
                Autonomous remapping and repair ensures zero-downtime resilience.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
