import { useState } from 'react';
import NLPGateway from './NLPGateway';
import PersonaDashboard from './PersonaDashboard';
import type { PersonaSlug } from '../types/persona';
import { slugToLabel, getPersonaIcon } from '../types/persona';

export default function ControlCenterPage() {
  const [selectedPersona, setSelectedPersona] = useState<PersonaSlug>('coo');

  const personas: PersonaSlug[] = ['cto', 'cro', 'coo', 'cfo'];

  return (
    <div className="space-y-8 px-4 sm:px-6 py-6">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-white mb-4">AOS Control Center</h1>
        <p className="text-lg text-gray-300 max-w-4xl leading-relaxed">
          Natural language interface to all AutonomOS services. Query your data, manage finances, investigate incidents, and discover dependencies—all through conversational AI with RAG-powered knowledge retrieval.
        </p>
      </div>

      {/* Persona Selector */}
      <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
        <div className="flex items-center gap-4">
          <label className="text-sm font-medium text-gray-300">Select Role:</label>
          <div className="flex gap-2">
            {personas.map((persona) => (
              <button
                key={persona}
                onClick={() => setSelectedPersona(persona)}
                className={`px-4 py-2 rounded-lg font-medium transition-all flex items-center gap-2 ${
                  selectedPersona === persona
                    ? 'bg-blue-600 text-white shadow-lg'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                }`}
              >
                <span>{getPersonaIcon(persona)}</span>
                <span>{slugToLabel(persona)}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Persona Dashboard */}
      <PersonaDashboard persona={selectedPersona} />

      {/* NLP Gateway */}
      <NLPGateway />
    </div>
  );
}
