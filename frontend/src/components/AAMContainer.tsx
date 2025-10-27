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

  // Helper to create chaotic wavy path with multiple control points
  const createChaoticPath = (x1: number, y1: number, x2: number, y2: number, variance: number) => {
    const segments = 3;
    let path = `M ${x1} ${y1}`;
    
    for (let i = 1; i <= segments; i++) {
      const t = i / segments;
      const x = x1 + (x2 - x1) * t;
      const y = y1 + (y2 - y1) * t;
      const offsetY = (Math.random() - 0.5) * variance;
      const offsetX = (Math.random() - 0.5) * variance * 0.5;
      
      if (i === segments) {
        path += ` L ${x2} ${y2}`;
      } else {
        path += ` L ${x + offsetX} ${y + offsetY}`;
      }
    }
    
    return path;
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

        {/* CONCEPT 1: Hub and Spoke Visualization */}
        <div className="mb-12">
          <h3 className="text-xl font-medium text-cyan-300 mb-4 text-center">Concept 1: Centralized Gateway (Hub & Spoke)</h3>
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

        {/* Divider */}
        <div className="my-16 border-t border-cyan-500/20"></div>

        {/* CONCEPT 2: Chaos to Order Transformation */}
        <div className="mb-12">
          <svg 
            viewBox="0 0 1000 400" 
            className="w-full max-w-6xl mx-auto"
          >
            <defs>
              {/* Gateway filter gradient */}
              <linearGradient id="gatewayGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stopColor="#06b6d4" stopOpacity="0.8" />
                <stop offset="50%" stopColor="#0e7490" stopOpacity="0.9" />
                <stop offset="100%" stopColor="#164e63" stopOpacity="0.8" />
              </linearGradient>
              
              {/* Glow for gateway */}
              <filter id="gatewayGlow">
                <feGaussianBlur stdDeviation="8" result="coloredBlur"/>
                <feMerge>
                  <feMergeNode in="coloredBlur"/>
                  <feMergeNode in="SourceGraphic"/>
                </feMerge>
              </filter>
            </defs>

            {/* LEFT: External Chaos - Disorganized logos with wavy one-to-one lines */}
            <g>
              {/* One-to-one wavy connection lines from each logo */}
              {dataSources.map((source, idx) => {
                const colors = ['#ef4444', '#f59e0b', '#10b981', '#3b82f6', '#8b5cf6', '#ec4899', '#f97316', '#14b8a6'];
                const logoSize = 32;
                const logoX = 50 + (idx % 2) * 60;
                const logoY = 60 + idx * 40;
                
                // Gateway entrance point (vertically distributed)
                const gatewayX = 400;
                const gatewayY = 80 + idx * 30;
                
                // Create smooth wavy path
                const midX1 = logoX + (gatewayX - logoX) * 0.33;
                const midY1 = logoY + (gatewayY - logoY) * 0.33 + (Math.sin(idx) * 20);
                const midX2 = logoX + (gatewayX - logoX) * 0.66;
                const midY2 = logoY + (gatewayY - logoY) * 0.66 + (Math.cos(idx) * 20);
                
                const wavyPath = `M ${logoX} ${logoY} C ${midX1} ${midY1}, ${midX2} ${midY2}, ${gatewayX} ${gatewayY}`;
                
                return (
                  <path
                    key={`chaos-${source.id}`}
                    d={wavyPath}
                    stroke={colors[idx % colors.length]}
                    strokeWidth="2"
                    fill="none"
                    opacity="0.6"
                  >
                    <animate
                      attributeName="opacity"
                      values="0.4;0.8;0.4"
                      dur={`${2 + idx * 0.3}s`}
                      repeatCount="indefinite"
                    />
                  </path>
                );
              })}
              
              {/* Chaotic logos cluster */}
              {dataSources.map((source, idx) => {
                const logoSize = 32;
                const x = 50 + (idx % 2) * 60;
                const y = 60 + idx * 40;
                
                return (
                  <g key={`chaos-logo-${source.id}`}>
                    <circle
                      cx={x}
                      cy={y}
                      r={logoSize / 2 + 3}
                      fill="rgba(15, 23, 42, 0.9)"
                      stroke="#475569"
                      strokeWidth="1"
                    />
                    <image
                      href={source.logo}
                      x={x - logoSize / 2}
                      y={y - logoSize / 2}
                      width={logoSize}
                      height={logoSize}
                    />
                  </g>
                );
              })}
              
              {/* "External Chaos" label */}
              <text x="80" y="30" fill="#94a3b8" fontSize="14" fontWeight="500">
                External Chaos
              </text>
            </g>

            {/* CENTER: AAM Gateway Filter/Portal */}
            <g>
              {/* Vertical filter portal */}
              <rect
                x="400"
                y="50"
                width="60"
                height="300"
                fill="url(#gatewayGradient)"
                filter="url(#gatewayGlow)"
                rx="10"
              >
                <animate
                  attributeName="opacity"
                  values="0.8;1;0.8"
                  dur="2s"
                  repeatCount="indefinite"
                />
              </rect>
              
              {/* Portal accent lines */}
              <line x1="410" y1="50" x2="410" y2="350" stroke="#06b6d4" strokeWidth="1" opacity="0.6" />
              <line x1="430" y1="50" x2="430" y2="350" stroke="#06b6d4" strokeWidth="1" opacity="0.6" />
              <line x1="450" y1="50" x2="450" y2="350" stroke="#06b6d4" strokeWidth="1" opacity="0.6" />
              
              {/* Gateway label */}
              <text x="430" y="380" textAnchor="middle" fill="#06b6d4" fontSize="16" fontWeight="600">
                AAM Gateway
              </text>
              
              {/* Floating words through gateway */}
              {['API Gateway', 'OAuth', 'Connector', 'Endpoint', 'Normalization', 'Schema', 'Trigger', 'Action', 'Batch Sync'].map((word, i) => (
                <text
                  key={`word-${i}`}
                  x="430"
                  y="100"
                  textAnchor="middle"
                  fill="#06b6d4"
                  fontSize="11"
                  fontWeight="500"
                  opacity="0"
                >
                  {word}
                  <animate
                    attributeName="y"
                    values="60;340"
                    dur="5s"
                    begin={`${i * 0.5}s`}
                    repeatCount="indefinite"
                  />
                  <animate
                    attributeName="opacity"
                    values="0;1;1;0"
                    keyTimes="0;0.1;0.9;1"
                    dur="5s"
                    begin={`${i * 0.5}s`}
                    repeatCount="indefinite"
                  />
                </text>
              ))}
            </g>

            {/* RIGHT: Normalized Order - Unified cyan streams */}
            <g>
              {/* Wavy streams flowing out from gateway */}
              {[0, 1, 2, 3, 4, 5, 6, 7].map((idx) => {
                const gatewayX = 460;
                const gatewayY = 80 + idx * 30;
                const endX = 920;
                const endY = 110 + idx * 30;
                
                // Create smooth wavy path to the right
                const midX1 = gatewayX + (endX - gatewayX) * 0.33;
                const midY1 = gatewayY + (endY - gatewayY) * 0.33 + (Math.sin(idx * 0.5) * 15);
                const midX2 = gatewayX + (endX - gatewayX) * 0.66;
                const midY2 = gatewayY + (endY - gatewayY) * 0.66 + (Math.cos(idx * 0.5) * 10);
                
                const wavyPath = `M ${gatewayX} ${gatewayY} C ${midX1} ${midY1}, ${midX2} ${midY2}, ${endX} ${endY}`;
                
                return (
                  <g key={`order-${idx}`}>
                    <path
                      d={wavyPath}
                      stroke="#06b6d4"
                      strokeWidth="3"
                      fill="none"
                      opacity="0.8"
                    >
                      <animate
                        attributeName="opacity"
                        values="0.6;1;0.6"
                        dur="2s"
                        repeatCount="indefinite"
                      />
                    </path>
                    
                    {/* Flow animation particle along the wavy path */}
                    <circle
                      r="4"
                      fill="#06b6d4"
                    >
                      <animateMotion
                        dur="3s"
                        begin={`${idx * 0.2}s`}
                        repeatCount="indefinite"
                        path={wavyPath}
                      />
                      <animate
                        attributeName="opacity"
                        values="0;1;0"
                        dur="3s"
                        begin={`${idx * 0.2}s`}
                        repeatCount="indefinite"
                      />
                    </circle>
                  </g>
                );
              })}
              
              {/* "Normalized Order" label */}
              <text x="700" y="30" fill="#06b6d4" fontSize="14" fontWeight="500">
                Normalized Order
              </text>
              
              {/* Normalized data indicator */}
              <rect
                x="880"
                y="110"
                width="80"
                height="210"
                fill="none"
                stroke="#06b6d4"
                strokeWidth="2"
                strokeDasharray="5,5"
                rx="8"
              />
              <text x="920" y="360" textAnchor="middle" fill="#06b6d4" fontSize="12">
                Normalized Data
              </text>
            </g>
          </svg>

          {/* Description for Concept 2 */}
          <div className="max-w-4xl mx-auto mt-8 bg-slate-900/80 rounded-lg border border-slate-700/50 p-6">
            <h3 className="text-xl font-medium text-cyan-400 mb-3">Transformation Layer</h3>
            <p className="text-lg text-slate-300 leading-relaxed">
              The AAM acts as a resilient shield, transforming disparate, chaotic external data sources 
              into normalized, unified streams. Varied schemas, protocols, and data formats are 
              harmonized into a consistent, governable flow—delivering order from chaos with 
              zero configuration required.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
