import { useState, useEffect } from 'react';
import { CheckCircle, AlertCircle, Info, Activity } from 'lucide-react';

interface DataSource {
  id: string;
  name: string;
  angle: number; // Position in arc (degrees)
  color: string;
}

interface ConnectionLog {
  time: string;
  type: 'success' | 'warning' | 'info' | 'healing';
  message: string;
  source?: string;
}

const dataSources: DataSource[] = [
  { id: 'salesforce', name: 'Salesforce', angle: 0, color: '#00A1E0' },
  { id: 'sap', name: 'SAP', angle: 45, color: '#0FAAFF' },
  { id: 'mongodb', name: 'MongoDB', angle: 90, color: '#47A248' },
  { id: 'snowflake', name: 'Snowflake', angle: 135, color: '#29B5E8' },
  { id: 'dynamics', name: 'Dynamics', angle: 180, color: '#0078D4' },
  { id: 'netsuite', name: 'NetSuite', angle: 225, color: '#FF6600' },
  { id: 'databricks', name: 'DataBricks', angle: 270, color: '#FF3621' },
  { id: 'supabase', name: 'Supabase', angle: 315, color: '#3ECF8E' },
];

const healingSequence = [
  { source: 'sap', message: 'SAP schema drift detected...', type: 'warning' as const },
  { source: 'sap', message: 'Autonomous remapping initiated for SAP...', type: 'healing' as const },
  { source: 'sap', message: 'SAP connection restored ✓', type: 'success' as const },
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
      // Normal operation (4 seconds)
      await new Promise(resolve => setTimeout(resolve, 4000));
      
      // Pick a random source for drift
      const randomSource = dataSources[Math.floor(Math.random() * dataSources.length)];
      setHealingSource(randomSource.id);
      
      // Phase 1: Drift detected (red flash)
      setHealingPhase('drift');
      const driftTime = new Date().toLocaleTimeString('en-US', { hour12: false });
      setLogs(prev => [
        { time: driftTime, type: 'warning', message: `${randomSource.name} schema drift detected...`, source: randomSource.id },
        ...prev.slice(0, 19)
      ]);
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      // Phase 2: Healing in progress
      setHealingPhase('healing');
      const healTime = new Date().toLocaleTimeString('en-US', { hour12: false });
      setLogs(prev => [
        { time: healTime, type: 'healing', message: `Autonomous remapping initiated for ${randomSource.name}...`, source: randomSource.id },
        ...prev.slice(0, 19)
      ]);
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // Phase 3: Restored (green)
      setHealingPhase('restored');
      const restoreTime = new Date().toLocaleTimeString('en-US', { hour12: false });
      setLogs(prev => [
        { time: restoreTime, type: 'success', message: `${randomSource.name} connection restored ✓`, source: randomSource.id },
        ...prev.slice(0, 19)
      ]);
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      // Reset
      setHealingPhase('normal');
      setHealingSource(null);
      setCycleCount(c => c + 1);
    };

    cycle();
    const interval = setInterval(cycle, 9000); // Full cycle every 9 seconds
    return () => clearInterval(interval);
  }, [cycleCount]);

  return (
    <div className="bg-black border-t border-b border-cyan-500/30 py-12 -mx-6 px-6">
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
          style={{ filter: 'drop-shadow(0 0 20px rgba(6, 182, 212, 0.3))' }}
        >
          {/* Connection Lines */}
          {dataSources.map((source) => {
            const radius = 180;
            const centerX = 400;
            const centerY = 250;
            const angleRad = (source.angle - 90) * (Math.PI / 180);
            const x = centerX + radius * Math.cos(angleRad);
            const y = centerY + radius * Math.sin(angleRad);
            
            const isHealing = healingSource === source.id;
            let strokeColor = '#06b6d4'; // cyan-500
            let strokeWidth = 2;
            let opacity = 0.6;
            
            if (isHealing) {
              if (healingPhase === 'drift') {
                strokeColor = '#ef4444'; // red-500
                strokeWidth = 3;
                opacity = 1;
              } else if (healingPhase === 'healing') {
                strokeColor = '#f59e0b'; // amber-500
                strokeWidth = 3;
                opacity = 1;
              } else if (healingPhase === 'restored') {
                strokeColor = '#22c55e'; // green-500
                strokeWidth = 3;
                opacity = 1;
              }
            }

            return (
              <g key={source.id}>
                <line
                  x1={centerX}
                  y1={centerY}
                  x2={x}
                  y2={y}
                  stroke={strokeColor}
                  strokeWidth={strokeWidth}
                  opacity={opacity}
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
                </line>
                
                {/* Pulse animation for healing */}
                {isHealing && healingPhase === 'healing' && (
                  <line
                    x1={centerX}
                    y1={centerY}
                    x2={x}
                    y2={y}
                    stroke={strokeColor}
                    strokeWidth={strokeWidth + 2}
                    opacity={0.3}
                  >
                    <animate
                      attributeName="opacity"
                      values="0;0.6;0"
                      dur="1s"
                      repeatCount="indefinite"
                    />
                  </line>
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
            
            {/* AAM text */}
            <text
              x="400"
              y="250"
              textAnchor="middle"
              fill="white"
              fontSize="16"
              fontWeight="600"
            >
              AAM
            </text>
            <text
              x="400"
              y="265"
              textAnchor="middle"
              fill="#06b6d4"
              fontSize="10"
            >
              CORE
            </text>
          </g>

          {/* Data Source Nodes */}
          {dataSources.map((source) => {
            const radius = 180;
            const centerX = 400;
            const centerY = 250;
            const angleRad = (source.angle - 90) * (Math.PI / 180);
            const x = centerX + radius * Math.cos(angleRad);
            const y = centerY + radius * Math.sin(angleRad);
            
            const isHealing = healingSource === source.id;
            let nodeColor = source.color;
            let nodeSize = 12;
            
            if (isHealing) {
              nodeSize = 16;
              if (healingPhase === 'drift') {
                nodeColor = '#ef4444';
              } else if (healingPhase === 'healing') {
                nodeColor = '#f59e0b';
              } else if (healingPhase === 'restored') {
                nodeColor = '#22c55e';
              }
            }

            return (
              <g key={source.id}>
                {/* Node glow */}
                <circle
                  cx={x}
                  cy={y}
                  r={nodeSize + 4}
                  fill={nodeColor}
                  opacity="0.3"
                />
                {/* Node */}
                <circle
                  cx={x}
                  cy={y}
                  r={nodeSize}
                  fill={nodeColor}
                  className="transition-all duration-500"
                >
                  {!isHealing && (
                    <animate
                      attributeName="opacity"
                      values="1;0.7;1"
                      dur="2s"
                      repeatCount="indefinite"
                    />
                  )}
                </circle>
                {/* Label */}
                <text
                  x={x}
                  y={y - nodeSize - 8}
                  textAnchor="middle"
                  fill="white"
                  fontSize="11"
                  fontWeight="500"
                >
                  {source.name}
                </text>
              </g>
            );
          })}

          {/* Gradients */}
          <defs>
            <linearGradient id="hexagonGradient" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#0e7490" />
              <stop offset="100%" stopColor="#164e63" />
            </linearGradient>
          </defs>
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
  );
}
