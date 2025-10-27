import { Database, Brain, Shield, Network, Eye, Wrench, Activity, Zap } from 'lucide-react';

const AdaptiveAPIMesh = () => {

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

        <div className="relative flex items-center justify-center min-h-[600px] perspective-800">
          <div className="relative card-container" style={{ transformStyle: 'preserve-3d' }}>
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
      </div>

      <style>{`
        .perspective-800 {
          perspective: 800px;
        }

        .card-container {
          transform-style: preserve-3d;
        }

        .isometric-layer {
          position: absolute;
          width: 500px;
          transition: transform 0.3s ease;
          transform-origin: center center;
        }

        .layer-1 {
          transform: rotateY(15deg) translateZ(-50px) translateY(-12px) translateX(-280px);
          z-index: 1;
        }

        .layer-2 {
          transform: rotateY(15deg) translateZ(-25px) translateY(-6px) translateX(0px);
          z-index: 2;
        }

        .layer-3 {
          transform: rotateY(15deg) translateZ(0px) translateX(280px);
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
            0 15px 30px -8px rgba(0, 0, 0, 0.4),
            inset 0 2px 4px rgba(255, 255, 255, 0.05);
        }

        .layer-2 .layer-content {
          box-shadow:
            0 25px 50px -10px rgba(11, 202, 217, 0.5),
            0 20px 40px -10px rgba(0, 0, 0, 0.4),
            inset 0 2px 4px rgba(255, 255, 255, 0.2);
        }

        .layer-3 .layer-content {
          box-shadow:
            0 35px 70px -12px rgba(11, 202, 217, 0.3),
            0 30px 60px -15px rgba(0, 0, 0, 0.5),
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
            width: 400px;
          }

          .layer-1 {
            transform: rotateY(15deg) translateZ(-40px) translateY(-10px) translateX(-220px);
          }

          .layer-2 {
            transform: rotateY(15deg) translateZ(-20px) translateY(-5px) translateX(0px);
          }

          .layer-3 {
            transform: rotateY(15deg) translateZ(0px) translateX(220px);
          }
        }

        @media (max-width: 768px) {
          .isometric-layer {
            position: relative;
            width: 100%;
            max-width: 400px;
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
