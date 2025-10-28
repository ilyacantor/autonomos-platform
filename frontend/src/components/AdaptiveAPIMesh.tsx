import { useState, useRef, useEffect } from 'react';
import { Database, Brain, Shield, Network, Eye, Wrench, Activity, Zap } from 'lucide-react';

interface LogMessage {
  time: string;
  type: 'success' | 'warning' | 'error';
  message: string;
}

const AdaptiveAPIMesh = () => {
  const [rotation, setRotation] = useState({ x: 10, y: 10 });
  const containerRef = useRef<HTMLDivElement>(null);
  const [isInteracting, setIsInteracting] = useState(false);
  const [messages, setMessages] = useState<LogMessage[]>([
    { time: '06:34:49', type: 'success', message: 'SAP connection restored ✓' },
    { time: '06:34:48', type: 'warning', message: 'Autonomous remapping initiated for NetSuite...' },
    { time: '06:34:46', type: 'error', message: 'NetSuite schema drift detected...' },
  ]);
  const logRef = useRef<HTMLDivElement>(null);

  const messagePool = [
    { type: 'success' as const, message: 'SAP connection restored ✓' },
    { type: 'success' as const, message: 'Snowflake connection restored ✓' },
    { type: 'success' as const, message: 'Salesforce connection restored ✓' },
    { type: 'success' as const, message: 'Dynamics connection restored ✓' },
    { type: 'success' as const, message: 'HubSpot connection restored ✓' },
    { type: 'warning' as const, message: 'Autonomous remapping initiated for SAP...' },
    { type: 'warning' as const, message: 'Autonomous remapping initiated for NetSuite...' },
    { type: 'warning' as const, message: 'Autonomous remapping initiated for Salesforce...' },
    { type: 'warning' as const, message: 'Autonomous remapping initiated for Dynamics...' },
    { type: 'error' as const, message: 'SAP schema drift detected...' },
    { type: 'error' as const, message: 'NetSuite schema drift detected...' },
    { type: 'error' as const, message: 'Salesforce schema drift detected...' },
    { type: 'error' as const, message: 'Dynamics schema drift detected...' },
    { type: 'error' as const, message: 'Snowflake schema drift detected...' },
  ];

  useEffect(() => {
    const interval = setInterval(() => {
      const now = new Date();
      const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;
      const randomMessage = messagePool[Math.floor(Math.random() * messagePool.length)];
      
      setMessages(prev => {
        const newMessages = [...prev, { time: timeStr, ...randomMessage }];
        return newMessages.slice(-20); // Keep last 20 messages
      });

      // Auto-scroll to bottom
      setTimeout(() => {
        if (logRef.current) {
          logRef.current.scrollTop = logRef.current.scrollHeight;
        }
      }, 50);
    }, 2500); // New message every 2.5 seconds

    return () => clearInterval(interval);
  }, []);

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!containerRef.current) return;

    const rect = containerRef.current.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width;
    const y = (e.clientY - rect.top) / rect.height;

    const rotateY = 10 + (x - 0.5) * 80;
    const rotateX = 10 + (y - 0.5) * -40;

    setRotation({ x: rotateX, y: rotateY });
  };

  const handleTouchMove = (e: React.TouchEvent<HTMLDivElement>) => {
    if (!containerRef.current || e.touches.length === 0) return;

    const rect = containerRef.current.getBoundingClientRect();
    const touch = e.touches[0];
    const x = (touch.clientX - rect.left) / rect.width;
    const y = (touch.clientY - rect.top) / rect.height;

    const rotateY = 10 + (x - 0.5) * 80;
    const rotateX = 10 + (y - 0.5) * -40;

    setRotation({ x: rotateX, y: rotateY });
  };

  const handleMouseLeave = () => {
    setIsInteracting(false);
    setRotation({ x: 10, y: 10 });
  };

  const handleMouseEnter = () => {
    setIsInteracting(true);
  };

  return (
    <div className="w-full bg-[#000000] py-16 px-4">
      <div className="max-w-7xl mx-auto">
        <div className="mb-12 text-center">
          <h2 className="text-4xl font-bold text-[#0BCAD9] mb-4">
            Adaptive API Mesh (AAM)
          </h2>
          <p className="text-gray-400 text-lg max-w-3xl mx-auto">
            A three-layer architecture combining universal connectivity with proprietary self-healing intelligence
          </p>
        </div>

        <div
          ref={containerRef}
          className="relative flex items-center justify-center min-h-[600px] perspective-1200 overflow-hidden cursor-grab active:cursor-grabbing"
          onMouseMove={handleMouseMove}
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
          onTouchMove={handleTouchMove}
          onTouchEnd={handleMouseLeave}
        >
          <div
            className="relative card-container mx-auto"
            style={{
              transformStyle: 'preserve-3d',
              transform: `rotateX(${rotation.x}deg) rotateY(${rotation.y}deg)`,
              transition: isInteracting ? 'transform 0.1s ease-out' : 'transform 0.5s ease-out'
            }}
          >
            <div className="isometric-layer layer-1">
              <div className="layer-content bg-gradient-to-br from-[#1a2332] to-[#0f1721] border-2 border-gray-600/40">
                <div className="layer-header">
                  <Database className="w-8 h-8 text-gray-400" />
                  <div>
                    <h3 className="text-xl font-bold text-gray-300">Execution Plane</h3>
                    <p className="text-sm text-gray-500">Adopted Infrastructure</p>
                  </div>
                </div>
                <div className="layer-features">
                  <div className="feature-item">
                    <Network className="w-5 h-5 text-gray-400" />
                    <span className="text-gray-400">Universal Connectivity</span>
                  </div>
                  <div className="feature-item">
                    <Shield className="w-5 h-5 text-gray-400" />
                    <span className="text-gray-400">API Gateway & Security</span>
                  </div>
                  <div className="feature-item">
                    <Activity className="w-5 h-5 text-gray-400" />
                    <span className="text-gray-400">Data Synchronization</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="isometric-layer layer-2">
              <div className="layer-content bg-gradient-to-br from-[#0BCAD9] to-[#0891b2] border-2 border-[#0BCAD9] relative overflow-hidden">
                <div className="absolute inset-0 bg-[#0BCAD9]/10 backdrop-blur-sm"></div>
                <div className="absolute inset-0 animate-pulse-glow"></div>
                <div className="relative z-10 layer-header">
                  <Brain className="w-8 h-8 text-white drop-shadow-lg" />
                  <div>
                    <h3 className="text-xl font-bold text-white drop-shadow-md">Adaptive Intelligence Plane</h3>
                    <p className="text-sm text-white/90 font-medium">Self-Healing Core</p>
                  </div>
                </div>
                <div className="relative z-10 layer-features">
                  <div className="feature-item">
                    <Zap className="w-5 h-5 text-white" />
                    <span className="text-white font-medium">RAG Engine (Autonomous Repair)</span>
                  </div>
                  <div className="feature-item">
                    <Eye className="w-5 h-5 text-white" />
                    <span className="text-white font-medium">Real-time Schema Observation</span>
                  </div>
                  <div className="feature-item">
                    <Wrench className="w-5 h-5 text-white" />
                    <span className="text-white font-medium">Drift Detection</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="isometric-layer layer-3">
              <div className="layer-content bg-gradient-to-br from-[#e0f2fe]/95 to-[#bae6fd]/95 border-2 border-[#0BCAD9]/50 backdrop-blur-md">
                <div className="layer-header">
                  <Shield className="w-8 h-8 text-[#0891b2]" />
                  <div>
                    <h3 className="text-xl font-bold text-[#0a4a5e]">Control Plane</h3>
                    <p className="text-sm text-[#0a4a5e]/70 font-medium">Governance & Monitoring</p>
                  </div>
                </div>
                <div className="layer-features">
                  <div className="feature-item">
                    <Activity className="w-5 h-5 text-[#0891b2]" />
                    <span className="text-[#0a4a5e]">AOS Control Center</span>
                  </div>
                  <div className="feature-item">
                    <Zap className="w-5 h-5 text-[#0891b2]" />
                    <span className="text-[#0a4a5e]">Real-time Alerting</span>
                  </div>
                  <div className="feature-item">
                    <Eye className="w-5 h-5 text-[#0891b2]" />
                    <span className="text-[#0a4a5e]">Human-in-the-Loop (HITL)</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-12 text-center">
          <p className="text-gray-300 text-lg max-w-3xl mx-auto">
            Connects data, on-prem systems, databases, SaaS platforms, APIs, CSV, and Agents through intelligent, self-healing infrastructure
          </p>
        </div>

        <div className="mt-16 grid grid-cols-1 lg:grid-cols-2 gap-8">
          <div className="bg-[#0A1628] border border-gray-700/50 rounded-lg p-6">
            <div className="flex items-center gap-2 mb-4">
              <Activity className="w-5 h-5 text-[#0BCAD9]" />
              <h3 className="text-lg font-semibold text-white">Real-time Connection Monitor</h3>
              <div className="ml-auto w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
            </div>
            <div ref={logRef} className="bg-[#000000] rounded-md p-4 font-mono text-sm h-64 overflow-y-auto">
              <div className="space-y-2">
                {messages.map((msg, index) => (
                  <div key={index} className="flex items-start gap-2">
                    <span className="text-gray-500 text-xs">{msg.time}</span>
                    <span className={
                      msg.type === 'success' ? 'text-green-400' :
                      msg.type === 'warning' ? 'text-yellow-400' :
                      'text-red-400'
                    }>
                      {msg.type === 'success' ? '✓' : msg.type === 'warning' ? '⚡' : '⚠'}
                    </span>
                    <span className={
                      msg.type === 'success' ? 'text-gray-300' :
                      msg.type === 'warning' ? 'text-yellow-300' :
                      'text-gray-300'
                    }>
                      {msg.message}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="space-y-8">
            <div>
              <h3 className="text-2xl font-bold text-[#0BCAD9] mb-4">Three-Layer Architecture</h3>
              <p className="text-gray-300 text-base leading-relaxed">
                The AAM is built on a robust foundation (Execution), powered by proprietary self-healing intelligence (Adaptive Intelligence), and managed through a unified control interface (AOS Control Center).
              </p>
            </div>

            <div>
              <h3 className="text-2xl font-bold text-[#0BCAD9] mb-4">Self-Healing Intelligence</h3>
              <p className="text-gray-300 text-base leading-relaxed">
                The centerpiece Adaptive Intelligence layer continuously monitors, detects drift, and autonomously repairs connections—ensuring zero-downtime resilience.
              </p>
            </div>
          </div>
        </div>
      </div>

      <style>{`
        .perspective-1200 {
          perspective: 1200px;
          perspective-origin: 50% 50%;
        }

        .card-container {
          transform-style: preserve-3d;
          width: 1050px;
          max-width: 100%;
          height: 375px;
          position: relative;
        }

        .isometric-layer {
          position: absolute;
          width: 360px;
          transition: transform 0.5s ease;
          transform-origin: center center;
          transform-style: preserve-3d;
          left: 50%;
          top: 50%;
          margin-left: -180px;
          margin-top: -112px;
        }

        .layer-1 {
          transform: rotateY(-10deg) translateZ(-112px) translateX(-300px) translateY(22px);
          z-index: 1;
        }

        .layer-2 {
          transform: rotateY(0deg) translateZ(0px) translateX(0px) translateY(0px);
          z-index: 2;
        }

        .layer-3 {
          transform: rotateY(-5deg) translateZ(112px) translateX(300px) translateY(-22px);
          z-index: 3;
        }

        .layer-content {
          padding: 2rem;
          border-radius: 16px;
          box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
          min-height: 200px;
          position: relative;
        }

        .layer-1 .layer-content {
          box-shadow:
            -40px 40px 80px -20px rgba(0, 0, 0, 0.7),
            -20px 20px 40px -10px rgba(0, 0, 0, 0.5),
            inset 0 2px 4px rgba(255, 255, 255, 0.05);
        }

        .layer-2 .layer-content {
          box-shadow:
            0 60px 120px -20px rgba(11, 202, 217, 0.6),
            0 40px 80px -15px rgba(0, 0, 0, 0.6),
            0 20px 40px -10px rgba(0, 0, 0, 0.4),
            inset 0 2px 4px rgba(255, 255, 255, 0.2);
        }

        .layer-3 .layer-content {
          box-shadow:
            40px 40px 100px -15px rgba(11, 202, 217, 0.5),
            30px 30px 80px -15px rgba(11, 202, 217, 0.4),
            20px 20px 60px -10px rgba(0, 0, 0, 0.5),
            inset 0 2px 4px rgba(255, 255, 255, 0.3);
        }

        .layer-header {
          display: flex;
          align-items: center;
          gap: 1rem;
          margin-bottom: 1.5rem;
        }

        .layer-features {
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
        }

        .feature-item {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          padding: 0.5rem;
          border-radius: 6px;
          background: rgba(0, 0, 0, 0.1);
          font-size: 0.875rem;
        }

        .layer-2 .feature-item {
          background: rgba(255, 255, 255, 0.1);
        }

        .layer-3 .feature-item {
          background: rgba(8, 145, 178, 0.08);
        }

        @keyframes pulse-glow {
          0%, 100% {
            opacity: 0.1;
          }
          50% {
            opacity: 0.2;
          }
        }

        .animate-pulse-glow {
          background: radial-gradient(circle at center, rgba(255, 255, 255, 0.3) 0%, transparent 70%);
          animation: pulse-glow 3s ease-in-out infinite;
        }

        @media (max-width: 1024px) {
          .isometric-layer {
            width: 300px;
          }

          .layer-1 {
            transform: rotateY(-10deg) translateZ(-90px) translateX(-240px) translateY(15px);
          }

          .layer-2 {
            transform: rotateY(0deg) translateZ(0px) translateX(0px) translateY(0px);
          }

          .layer-3 {
            transform: rotateY(-5deg) translateZ(90px) translateX(240px) translateY(-15px);
          }
        }

        @media (max-width: 768px) {
          .perspective-1200 {
            cursor: default !important;
          }

          .isometric-layer {
            position: relative;
            width: 100%;
            max-width: 300px;
            margin: 0 auto 2rem;
            transform: none !important;
          }

          .layer-1, .layer-2, .layer-3 {
            position: relative;
            transform: none !important;
          }
        }
      `}</style>
    </div>
  );
};

export default AdaptiveAPIMesh;
