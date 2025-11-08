import { useState } from 'react';
import { Send, Loader2, BookOpen, DollarSign, AlertCircle, Network, Database } from 'lucide-react';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  trace_id?: string;
  sources?: string[];
}

export default function NLPGateway() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [selectedService, setSelectedService] = useState<string>('kb');

  const services = [
    { id: 'kb', name: 'Knowledge Base', icon: BookOpen, endpoint: '/v1/kb/search' },
    { id: 'finops', name: 'FinOps', icon: DollarSign, endpoint: '/v1/finops/summary' },
    { id: 'revops', name: 'RevOps', icon: AlertCircle, endpoint: '/v1/revops/incident' },
    { id: 'aod', name: 'Discovery', icon: Network, endpoint: '/v1/aod/dependencies' },
    { id: 'aam', name: 'Connectors', icon: Database, endpoint: '/v1/aam/connectors' },
  ];

  const prompts = [
    'Show me the FinOps summary for this month',
    'How does the AAM connector system work?',
    'What are the current drifted connectors?',
    'Show me dependencies for checkout-service',
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage: Message = { role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const token = localStorage.getItem('token');
      const service = services.find(s => s.id === selectedService);
      
      let endpoint = `http://localhost:8001${service?.endpoint}`;
      let payload: any = {
        tenant_id: 'demo-tenant',
        env: 'prod',
      };

      if (selectedService === 'kb') {
        payload.query = input;
        payload.top_k = 5;
      } else if (selectedService === 'finops') {
        const now = new Date();
        const firstDay = new Date(now.getFullYear(), now.getMonth(), 1);
        payload.from = firstDay.toISOString().split('T')[0];
        payload.to = now.toISOString().split('T')[0];
      } else if (selectedService === 'revops') {
        payload.incident_id = 'I-9A03';
      } else if (selectedService === 'aod') {
        payload.service = 'checkout-service';
      } else if (selectedService === 'aam') {
        payload.status = 'All';
      }

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': token ? `Bearer ${token}` : '',
        },
        body: JSON.stringify(payload),
      });

      const data = await response.json();
      
      let content = '';
      let sources: string[] = [];
      
      if (selectedService === 'kb' && data.matches) {
        content = data.matches.map((m: any, i: number) => 
          `${i + 1}. ${m.title}\n${m.content}\nScore: ${m.score.toFixed(3)}`
        ).join('\n\n');
        sources = data.matches.map((m: any) => `${m.title}: ${m.section}`);
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

  const handlePromptClick = (prompt: string) => {
    setInput(prompt);
  };

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
      <div className="bg-gradient-to-r from-green-900 to-blue-900 p-4 border-b border-gray-700">
        <h2 className="text-xl font-semibold text-white flex items-center gap-2">
          <BookOpen className="w-5 h-5" />
          AOS NLP Gateway
        </h2>
        <p className="text-gray-300 text-sm mt-1">Natural language interface to AutonomOS services</p>
      </div>

      <div className="p-4 space-y-4">
        <div className="flex gap-2 flex-wrap">
          {services.map(service => (
            <button
              key={service.id}
              onClick={() => setSelectedService(service.id)}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors flex items-center gap-1.5 ${
                selectedService === service.id
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              <service.icon className="w-4 h-4" />
              {service.name}
            </button>
          ))}
        </div>

        {messages.length === 0 && (
          <div className="space-y-3">
            <p className="text-gray-400 text-sm">Try these prompts:</p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {prompts.map((prompt, i) => (
                <button
                  key={i}
                  onClick={() => handlePromptClick(prompt)}
                  className="p-3 bg-gray-700 hover:bg-gray-600 rounded-lg text-left text-sm text-gray-300 transition-colors border border-gray-600"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="space-y-3 max-h-96 overflow-y-auto">
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`p-3 rounded-lg ${
                msg.role === 'user'
                  ? 'bg-blue-900 bg-opacity-30 border border-blue-700'
                  : 'bg-gray-700 border border-gray-600'
              }`}
            >
              <div className="text-xs text-gray-400 mb-1">
                {msg.role === 'user' ? 'You' : 'NLP Gateway'}
                {msg.trace_id && <span className="ml-2 font-mono">{msg.trace_id}</span>}
              </div>
              <div className="text-gray-200 whitespace-pre-wrap font-mono text-sm">
                {msg.content}
              </div>
              {msg.sources && msg.sources.length > 0 && (
                <div className="mt-2 pt-2 border-t border-gray-600">
                  <div className="text-xs text-gray-400 mb-1">Sources:</div>
                  <div className="flex flex-wrap gap-1">
                    {msg.sources.map((source, i) => (
                      <span key={i} className="text-xs bg-gray-600 px-2 py-0.5 rounded text-gray-300">
                        {source}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question or make a request..."
            className="flex-1 px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:cursor-not-allowed rounded-lg text-white font-medium transition-colors flex items-center gap-2"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Thinking
              </>
            ) : (
              <>
                <Send className="w-4 h-4" />
                Send
              </>
            )}
          </button>
        </form>

        <div className="text-xs text-gray-500 mt-2">
          Port: 8001 | Tenant: demo-tenant | Env: prod | Auth: JWT
        </div>
      </div>
    </div>
  );
}
