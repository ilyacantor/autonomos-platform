import { BookOpen, Layers, Cable, Database, Activity, Search, Sparkles, ArrowRight, CheckCircle } from 'lucide-react';

export default function GuidePage() {
  const platformLayers = [
    {
      name: 'Discovery (AOD)',
      description: 'Asset & Observability Discovery - The Senses',
      icon: <Search className="w-6 h-6" />,
      color: 'from-emerald-500 to-emerald-600',
      capabilities: [
        'Fabric Plane Identification (MuleSoft, Kafka, Snowflake)',
        'Enterprise Preset Inference (Scrappy vs Platform)',
        'Asset Discovery & Cataloging',
        'Policy Manifest Export'
      ]
    },
    {
      name: 'Mesh (AAM)',
      description: 'Adaptive API Mesh - The Fabric',
      icon: <Cable className="w-6 h-6" />,
      color: 'from-blue-500 to-blue-600',
      capabilities: [
        'Fabric Plane Connection (Backbone)',
        'Preset Config Loading (6, 8, 9, 11)',
        'Self-Healing & Drift Detection',
        'PII Redaction at Edge'
      ]
    },
    {
      name: 'Connectivity (DCL)',
      description: 'Data Connectivity Layer - The Brain',
      icon: <Database className="w-6 h-6" />,
      color: 'from-purple-500 to-purple-600',
      capabilities: [
        'Fabric Pointer Buffering (Zero-Trust)',
        'Just-in-Time Payload Fetching',
        'Schema Drift Detection',
        'Downstream Consumer Protocol'
      ]
    },
    {
      name: 'Orchestration (AOA)',
      description: 'Agentic Orchestration Architecture - The Hands',
      icon: <Activity className="w-6 h-6" />,
      color: 'from-orange-500 to-orange-600',
      capabilities: [
        'Fabric Action Routing',
        'Transaction Execution',
        'Worker Pool Management',
        'Context Sanitization'
      ]
    }
  ];

  const fabricPresets = [
    { id: 6, name: 'Scrappy', description: 'Direct P2P API connections (startup/dev mode)' },
    { id: 8, name: 'iPaaS-Centric', description: 'Integration logic flows via iPaaS (Workato, MuleSoft)' },
    { id: 9, name: 'Platform-Oriented', description: 'High-volume data via Event Bus (Kafka)' },
    { id: 11, name: 'Warehouse-Centric', description: 'Source of Truth is Data Warehouse (Snowflake)' }
  ];

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-8">
      <div className="text-center mb-8">
        <div className="flex items-center justify-center gap-3 mb-4">
          <BookOpen className="w-10 h-10 text-cyan-400" />
          <h1 className="text-3xl font-bold text-white">Platform Guide</h1>
        </div>
        <p className="text-gray-400 text-lg max-w-2xl mx-auto">
          AutonomOS is an AI-native operating system for the enterprise data/agent stack.
          It connects chaotic source systems to domain agents via a unified Fabric Plane Mesh.
        </p>
      </div>

      <div className="bg-gray-800/50 rounded-xl p-6 border border-gray-700">
        <h2 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
          <Layers className="w-5 h-5 text-cyan-400" />
          Fabric Plane Mesh Architecture
        </h2>
        <p className="text-gray-400 mb-6">
          AAM (The Mesh) connects to Fabric Planes that aggregate data, NOT directly to individual SaaS applications.
          This architecture supports enterprise-grade patterns with self-healing connections.
        </p>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          {fabricPresets.map((preset) => (
            <div key={preset.id} className="bg-gray-900/50 rounded-lg p-4 border border-gray-700">
              <div className="flex items-center gap-2 mb-2">
                <span className="bg-cyan-500/20 text-cyan-400 px-2 py-0.5 rounded text-sm font-mono">
                  Preset {preset.id}
                </span>
                <span className="text-white font-medium">{preset.name}</span>
              </div>
              <p className="text-gray-400 text-sm">{preset.description}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="space-y-4">
        <h2 className="text-xl font-semibold text-white flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-cyan-400" />
          Platform Layers
        </h2>
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {platformLayers.map((layer, index) => (
            <div key={layer.name} className="bg-gray-800/50 rounded-xl p-5 border border-gray-700 hover:border-gray-600 transition-colors">
              <div className="flex items-start gap-4">
                <div className={`p-3 rounded-lg bg-gradient-to-br ${layer.color} text-white`}>
                  {layer.icon}
                </div>
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-white mb-1">{layer.name}</h3>
                  <p className="text-gray-400 text-sm mb-3">{layer.description}</p>
                  <ul className="space-y-1.5">
                    {layer.capabilities.map((cap, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-gray-300">
                        <CheckCircle className="w-4 h-4 text-green-400 mt-0.5 flex-shrink-0" />
                        <span>{cap}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-gray-800/50 rounded-xl p-6 border border-gray-700">
        <h2 className="text-xl font-semibold text-white mb-4">Data Flow</h2>
        <div className="flex items-center justify-center gap-2 flex-wrap text-sm">
          <span className="bg-emerald-500/20 text-emerald-400 px-3 py-1.5 rounded-lg font-medium">
            AOD (Discover)
          </span>
          <ArrowRight className="w-5 h-5 text-gray-500" />
          <span className="bg-blue-500/20 text-blue-400 px-3 py-1.5 rounded-lg font-medium">
            AAM (Connect)
          </span>
          <ArrowRight className="w-5 h-5 text-gray-500" />
          <span className="bg-purple-500/20 text-purple-400 px-3 py-1.5 rounded-lg font-medium">
            DCL (Unify)
          </span>
          <ArrowRight className="w-5 h-5 text-gray-500" />
          <span className="bg-orange-500/20 text-orange-400 px-3 py-1.5 rounded-lg font-medium">
            AOA (Orchestrate)
          </span>
          <ArrowRight className="w-5 h-5 text-gray-500" />
          <span className="bg-cyan-500/20 text-cyan-400 px-3 py-1.5 rounded-lg font-medium">
            Agents (Action)
          </span>
        </div>
      </div>

      <div className="bg-gradient-to-r from-cyan-900/30 to-blue-900/30 rounded-xl p-6 border border-cyan-800/50">
        <h2 className="text-xl font-semibold text-white mb-3">Getting Started</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-gray-900/50 rounded-lg p-4">
            <div className="text-cyan-400 font-semibold mb-2">1. Discover</div>
            <p className="text-gray-400 text-sm">Navigate to Discovery to scan your infrastructure and identify Fabric Planes.</p>
          </div>
          <div className="bg-gray-900/50 rounded-lg p-4">
            <div className="text-cyan-400 font-semibold mb-2">2. Connect</div>
            <p className="text-gray-400 text-sm">Use the Connect page to establish self-healing connections to your Fabric Planes.</p>
          </div>
          <div className="bg-gray-900/50 rounded-lg p-4">
            <div className="text-cyan-400 font-semibold mb-2">3. Orchestrate</div>
            <p className="text-gray-400 text-sm">Visit Orchestration to configure and monitor your AI agents.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
