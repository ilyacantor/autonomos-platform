import { useState, useEffect } from 'react';
import { LayoutDashboard, Activity } from 'lucide-react';
import NLPGateway from './NLPGateway';
import PersonaDashboard from './PersonaDashboard';
import FlowMonitor from './FlowMonitor';
import type { PersonaSlug } from '../types/persona';
import { slugToLabel, getPersonaIcon } from '../types/persona';

const LEGACY_PERSONA_MAP: Record<string, PersonaSlug> = {
  'data_engineer': 'cto',
  'revops': 'cro',
  'finops': 'coo',
  'finance': 'cfo'
};

function getInitialPersona(): { persona: PersonaSlug; source: string } {
  const stored = localStorage.getItem('aos.persona');
  
  if (stored) {
    const legacy = LEGACY_PERSONA_MAP[stored];
    if (legacy) {
      localStorage.setItem('aos.persona', legacy);
      return { persona: legacy, source: 'localStorage (migrated)' };
    }
    
    if (['cto', 'cro', 'coo', 'cfo'].includes(stored)) {
      return { persona: stored as PersonaSlug, source: 'localStorage' };
    }
  }
  
  const token = localStorage.getItem('token');
  if (token) {
    try {
      const parts = token.split('.');
      if (parts.length === 3) {
        let base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
        while (base64.length % 4) {
          base64 += '=';
        }
        const payload = JSON.parse(atob(base64));
        if (payload.role && ['cto', 'cro', 'coo', 'cfo'].includes(payload.role)) {
          return { persona: payload.role as PersonaSlug, source: 'jwt' };
        }
      }
    } catch (e) {
      // Invalid token, ignore
    }
  }
  
  return { persona: 'coo', source: 'default' };
}

type SubTab = 'dashboard' | 'flow-monitor';

export default function ControlCenterPage() {
  const [selectedPersona, setSelectedPersona] = useState<PersonaSlug>(() => getInitialPersona().persona);
  const [activeSubTab, setActiveSubTab] = useState<SubTab>('dashboard');

  const personas: PersonaSlug[] = ['cto', 'cro', 'coo', 'cfo'];

  useEffect(() => {
    const { persona, source } = getInitialPersona();
    console.info(`[ControlCenter] persona=${persona} source=${source}`);
  }, []);

  useEffect(() => {
    localStorage.setItem('aos.persona', selectedPersona);
  }, [selectedPersona]);

  return (
    <div className="space-y-8 px-4 sm:px-6 py-6">
      {/* Mock-up Notice */}
      <div className="bg-gray-800/40 border border-gray-700/50 rounded-lg px-4 py-2">
        <p className="text-sm text-gray-400 text-center">
          <span className="font-medium text-gray-300">Demo Environment</span> • This interface demonstrates platform capabilities with static mock data
        </p>
      </div>

      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-white mb-4">AOS Control Center</h1>
        <p className="text-lg text-gray-300 leading-relaxed">
          Natural language interface to all AutonomOS services. Query your data, manage finances, investigate incidents, and discover dependencies—all through conversational AI with RAG-powered knowledge retrieval.
        </p>
      </div>

      {/* Subtabs */}
      <div className="flex gap-2 border-b border-gray-700">
        <button
          onClick={() => setActiveSubTab('dashboard')}
          className={`flex items-center gap-2 px-4 py-3 font-medium transition-all ${
            activeSubTab === 'dashboard'
              ? 'text-blue-400 border-b-2 border-blue-400'
              : 'text-gray-400 hover:text-gray-300'
          }`}
        >
          <LayoutDashboard className="w-4 h-4" />
          Dashboard
        </button>
        <button
          onClick={() => setActiveSubTab('flow-monitor')}
          className={`flex items-center gap-2 px-4 py-3 font-medium transition-all ${
            activeSubTab === 'flow-monitor'
              ? 'text-blue-400 border-b-2 border-blue-400'
              : 'text-gray-400 hover:text-gray-300'
          }`}
        >
          <Activity className="w-4 h-4" />
          Flow Monitor
        </button>
      </div>

      {/* Content */}
      {activeSubTab === 'dashboard' && (
        <div className="space-y-8">
          {/* Persona Selector */}
          <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
            <div className="flex items-center gap-4">
              <label className="text-sm font-medium text-gray-300">Select Role:</label>
              <div className="flex gap-2">
                {personas.map((persona) => {
                  const IconComponent = getPersonaIcon(persona);
                  return (
                    <button
                      key={persona}
                      onClick={() => setSelectedPersona(persona)}
                      className={`px-4 py-2 rounded-lg font-medium transition-all flex items-center gap-2 ${
                        selectedPersona === persona
                          ? 'bg-blue-600 text-white shadow-lg'
                          : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                      }`}
                    >
                      <IconComponent className="w-4 h-4" />
                      <span>{slugToLabel(persona)}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          {/* NLP Gateway */}
          <NLPGateway persona={selectedPersona} />

          {/* Persona Dashboard */}
          <PersonaDashboard persona={selectedPersona} />
        </div>
      )}

      {activeSubTab === 'flow-monitor' && (
        <div className="-mx-4 -mb-6 sm:-mx-6">
          <FlowMonitor />
        </div>
      )}
    </div>
  );
}
