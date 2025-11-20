import { useState } from 'react';
import { Send, Loader2, BookOpen, RotateCcw, HelpCircle } from 'lucide-react';
import LiveStatusBadge from './LiveStatusBadge';
import { getLiveStatus } from '../config/liveStatus';
import type { PersonaSlug } from '../types/persona';
import { slugToLabel } from '../types/persona';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  trace_id?: string;
  sources?: string[];
}

interface NLPGatewayProps {
  persona: PersonaSlug;
}

const PERSONA_PROMPTS: Record<PersonaSlug, string[]> = {
  cto: [
    'Any connector drift today?',
    'Show dependencies for checkout-service',
    'List degraded connectors',
    'What apps are missing owners?',
  ],
  cro: [
    'Show this quarter\'s pipeline by stage',
    'What\'s win rate vs last quarter?',
    'Which deals are slipping?',
    'Top 10 opportunities by value',
  ],
  coo: [
    'Cloud spend MTD vs budget',
    'Renewals due in 30 days',
    'Top cost centers MTD',
    'Vendors > $50k last 30d',
  ],
  cfo: [
    'Revenue MTD / QTD / YTD',
    'Gross margin trend',
    'Cash, burn, runway',
    'DSO / DPO last 90d',
  ],
};

export default function NLPGateway({ persona }: NLPGatewayProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [resolvedPersona, setResolvedPersona] = useState<string | null>(null);

  const prompts = PERSONA_PROMPTS[persona];

  const handleSubmit = async (e?: React.FormEvent, queryText?: string) => {
    if (e) e.preventDefault();
    
    const queryToSend = queryText || input;
    if (!queryToSend.trim() || loading) return;

    const userMessage: Message = { role: 'user', content: queryToSend };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const token = localStorage.getItem('token');
      
      const response = await fetch('/nlp/v1/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': token ? `Bearer ${token}` : '',
        },
        body: JSON.stringify({
          query: queryToSend,
          persona: persona,
        }),
      });

      const data = await response.json();
      
      // Update resolved persona if available
      if (data.resolved_persona) {
        setResolvedPersona(data.resolved_persona);
      }
      
      let content = '';
      let sources: string[] = [];
      
      if (data.matches) {
        content = data.matches.map((m: any, i: number) => 
          `${i + 1}. ${m.title}\n${m.content}\nScore: ${m.score.toFixed(3)}`
        ).join('\n\n');
        sources = data.matches.map((m: any) => `${m.title}: ${m.section}`);
      } else if (data.response) {
        content = data.response;
      } else {
        content = JSON.stringify(data, null, 2);
      }

      const assistantMessage: Message = {
        role: 'assistant',
        content,
        trace_id: data.trace_id,
        sources,
      };
      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage: Message = {
        role: 'assistant',
        content: `Error: ${error instanceof Error ? error.message : 'Failed to connect to NLP Gateway'}`,
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handlePromptClick = (promptText: string) => {
    setInput(promptText);
    handleSubmit(undefined, promptText);
  };

  const handleReset = () => {
    setMessages([]);
    setInput('');
  };

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
      <div className="bg-gradient-to-r from-green-900 to-blue-900 px-4 py-3 border-b border-gray-700 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <BookOpen className="w-5 h-5 text-white" />
          <h2 className="text-lg font-semibold text-white">AOS NLP Gateway</h2>
          <LiveStatusBadge {...getLiveStatus('nlp-gateway')!} />
          {messages.length > 0 && (
            <button
              onClick={handleReset}
              className="flex items-center gap-1 px-2 py-1 text-xs bg-red-600 hover:bg-red-700 text-white rounded transition-colors"
              title="Clear conversation"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Clear</span>
            </button>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-300 bg-gray-700 bg-opacity-50 px-2 py-1 rounded flex items-center gap-1.5">
            <span className="text-gray-400">Resolved:</span>
            <span className="font-medium text-white">
              {resolvedPersona ? slugToLabel(resolvedPersona as PersonaSlug) : slugToLabel(persona)}
            </span>
            <span className="text-gray-400">(Auto)</span>
          </span>
          <button
            className="flex items-center gap-1 px-2 py-1 text-xs text-gray-300 hover:text-white transition-colors group"
            title="Queries are automatically routed to the appropriate domain expertise based on detected persona"
          >
            <HelpCircle className="w-3.5 h-3.5 group-hover:text-blue-400" />
          </button>
        </div>
      </div>

      <div className="p-6 space-y-4">
        <form onSubmit={handleSubmit} className="flex gap-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask anything about AutonomOS services..."
            className="flex-1 px-6 py-4 text-lg bg-gray-700 border-2 border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            disabled={loading}
            autoFocus
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="px-6 py-4 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:cursor-not-allowed rounded-lg text-white font-semibold transition-colors flex items-center gap-2 text-lg"
          >
            {loading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Thinking
              </>
            ) : (
              <>
                <Send className="w-5 h-5" />
                Send
              </>
            )}
          </button>
        </form>

        <div className="space-y-3 bg-gray-900 bg-opacity-50 rounded-lg p-4 border border-gray-700">
          {messages.length === 0 ? (
            <div className="py-8">
              <div className="text-center space-y-4 max-w-2xl mx-auto">
                <p className="text-gray-400 text-sm mb-3">Get started with these {slugToLabel(persona)} prompts:</p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {prompts.map((promptText, i) => (
                    <button
                      key={i}
                      onClick={() => handlePromptClick(promptText)}
                      className="p-2 bg-gray-800 hover:bg-gray-700 rounded text-left text-xs text-gray-300 transition-colors border border-gray-700"
                    >
                      {promptText}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            messages.map((msg, i) => (
              <div
                key={i}
                className={`p-4 rounded-lg ${
                  msg.role === 'user'
                    ? 'bg-blue-900 bg-opacity-40 border border-blue-700'
                    : 'bg-gray-800 border border-gray-600'
                }`}
              >
                <div className="text-xs text-gray-400 mb-2 flex items-center justify-between">
                  <span className="font-semibold">
                    {msg.role === 'user' ? 'You' : 'NLP Gateway'}
                  </span>
                  {msg.trace_id && <span className="font-mono text-gray-500">{msg.trace_id}</span>}
                </div>
                <div className="text-gray-200 whitespace-pre-wrap font-mono text-sm">
                  {msg.content}
                </div>
                {msg.sources && msg.sources.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-gray-700">
                    <div className="text-xs text-gray-400 mb-2">Sources:</div>
                    <div className="flex flex-wrap gap-1">
                      {msg.sources.map((source, i) => (
                        <span key={i} className="text-xs bg-gray-700 px-2 py-1 rounded text-gray-300">
                          {source}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))
          )}
        </div>

        <div className="text-xs text-gray-500 text-center">
          Tenant: demo-tenant | Env: prod | Auth: JWT
        </div>
      </div>
    </div>
  );
}
