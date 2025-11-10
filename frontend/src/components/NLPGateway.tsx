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
      
      let endpoint = `/nlp${service?.endpoint}`;
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
      } else if (selectedService === 'finops' && data.summary) {
        const s = data.summary;
        content = `💰 FinOps Cost Summary\n\n` +
          `Total Cost: ${s.total_cost} (${s.vs_last_month} vs last month)\n\n` +
          `Top Services:\n` +
          s.top_services.map((svc: any) => `  • ${svc.name}: ${svc.cost}`).join('\n') +
          `\n\n💡 Savings Opportunities: ${s.savings_opportunities}`;
      } else if (selectedService === 'revops' && data.incident) {
        const i = data.incident;
        content = `🔧 Incident: ${i.incident_id}\n\n` +
          `Title: ${i.title}\n` +
          `Status: ${i.status}\n` +
          `Root Cause: ${i.root_cause}\n` +
          `Resolution: ${i.resolution}\n` +
          `Impact: ${i.impact}`;
      } else if (selectedService === 'aod' && data.dependencies) {
        content = `🔍 Service: ${data.service}\n` +
          `Health: ${data.health}\n\n` +
          `Upstream Dependencies:\n${data.dependencies.upstream.map((d: string) => `  • ${d}`).join('\n')}\n\n` +
          `Downstream Dependencies:\n${data.dependencies.downstream.map((d: string) => `  • ${d}`).join('\n')}`;
      } else if (selectedService === 'aam' && data.connectors) {
        content = `🔌 AAM Connectors (${data.total} total)\n\n` +
          data.connectors.map((c: any) => 
            `${c.status === 'Healthy' ? '✅' : '⚠️'} ${c.name}\n  Status: ${c.status}\n  Last Sync: ${c.last_sync}`
          ).join('\n\n');
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
      <div className="bg-gradient-to-r from-green-900 to-blue-900 px-4 py-3 border-b border-gray-700 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-white" />
          <h2 className="text-lg font-semibold text-white">AOS NLP Gateway</h2>
        </div>
        <div className="flex gap-2">
          {services.map(service => (
            <button
              key={service.id}
              onClick={() => setSelectedService(service.id)}
              className={`px-2 py-1 rounded text-xs font-medium transition-colors flex items-center gap-1 ${
                selectedService === service.id
                  ? 'bg-white bg-opacity-20 text-white'
                  : 'text-gray-300 hover:bg-white hover:bg-opacity-10'
              }`}
              title={service.name}
            >
              <service.icon className="w-3.5 h-3.5" />
              <span className="hidden md:inline">{service.name}</span>
            </button>
          ))}
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

        <div className="space-y-3 min-h-[400px] max-h-[500px] overflow-y-auto bg-gray-900 bg-opacity-50 rounded-lg p-4 border border-gray-700">
          {messages.length === 0 ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center space-y-4 max-w-2xl">
                <p className="text-gray-400 text-sm mb-3">Get started with these prompts:</p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {prompts.map((prompt, i) => (
                    <button
                      key={i}
                      onClick={() => handlePromptClick(prompt)}
                      className="p-2 bg-gray-800 hover:bg-gray-700 rounded text-left text-xs text-gray-300 transition-colors border border-gray-700"
                    >
                      {prompt}
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
