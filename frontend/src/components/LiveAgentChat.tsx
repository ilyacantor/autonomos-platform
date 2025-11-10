import { useState } from 'react';
import { Send, Loader2, RotateCcw, DollarSign, TrendingUp, AlertTriangle, Zap } from 'lucide-react';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

interface LiveAgentChatProps {
  agentType: 'finops' | 'revops';
  title: string;
  description: string;
}

export default function LiveAgentChat({ agentType, title, description }: LiveAgentChatProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  const agentConfig = {
    finops: {
      icon: DollarSign,
      color: 'green',
      endpoint: '/nlp/v1/finops/summary',
      suggestions: [
        'Show me the FinOps summary for this month',
        'What are the top cost drivers?',
        'Show me savings opportunities',
        'Compare costs vs last month',
      ],
      placeholder: 'Ask about cloud costs, budgets, or savings...',
    },
    revops: {
      icon: AlertTriangle,
      color: 'red',
      endpoint: '/nlp/v1/revops/incident',
      suggestions: [
        'Show me the latest incident details',
        'What was the root cause?',
        'Get incident resolution status',
        'Show me the impact analysis',
      ],
      placeholder: 'Ask about incidents, resolutions, or impact...',
    },
  };

  const config = agentConfig[agentType];
  const Icon = config.icon;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage: Message = {
      role: 'user',
      content: input,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      let payload: any = {
        tenant_id: 'demo-tenant',
        env: 'prod',
      };

      if (agentType === 'finops') {
        const now = new Date();
        const firstDay = new Date(now.getFullYear(), now.getMonth(), 1);
        payload.from = firstDay.toISOString().split('T')[0];
        payload.to = now.toISOString().split('T')[0];
      } else if (agentType === 'revops') {
        payload.incident_id = 'I-9A03';
      }

      const response = await fetch(config.endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      const data = await response.json();

      let content = '';

      if (agentType === 'finops' && data.summary) {
        const s = data.summary;
        content = `💰 **FinOps Cost Summary**\n\n` +
          `**Total Cost:** ${s.total_cost}\n` +
          `**vs Last Month:** ${s.vs_last_month}\n\n` +
          `**Top Services:**\n` +
          s.top_services.map((svc: any) => `  • ${svc.name}: ${svc.cost}`).join('\n') +
          `\n\n💡 **Savings Opportunities:** ${s.savings_opportunities}`;
      } else if (agentType === 'revops' && data.incident) {
        const i = data.incident;
        content = `🔧 **Incident ${i.incident_id}**\n\n` +
          `**Title:** ${i.title}\n` +
          `**Status:** ${i.status}\n` +
          `**Priority:** ${i.priority || 'High'}\n\n` +
          `**Root Cause:**\n${i.root_cause}\n\n` +
          `**Resolution:**\n${i.resolution}\n\n` +
          `**Impact:** ${i.impact}`;
      } else {
        content = JSON.stringify(data, null, 2);
      }

      const assistantMessage: Message = {
        role: 'assistant',
        content,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage: Message = {
        role: 'assistant',
        content: `❌ Error: ${error instanceof Error ? error.message : 'Failed to connect to agent'}`,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleSuggestion = (suggestion: string) => {
    setInput(suggestion);
  };

  const handleClear = () => {
    setMessages([]);
    setInput('');
  };

  return (
    <div className="bg-gray-800/50 border border-gray-700 rounded-lg overflow-hidden flex flex-col h-[500px]">
      {/* Header */}
      <div className={`px-4 py-3 bg-gradient-to-r from-${config.color}-900/30 to-transparent border-b border-gray-700`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`p-2 bg-${config.color}-500/20 rounded-lg`}>
              <Icon className={`w-5 h-5 text-${config.color}-400`} />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-white">{title}</h3>
              <p className="text-xs text-gray-400">{description}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5 px-2 py-1 bg-green-500/10 border border-green-500/30 rounded-full">
              <div className="w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse" />
              <span className="text-xs text-green-400 font-medium">Live</span>
            </div>
            {messages.length > 0 && (
              <button
                onClick={handleClear}
                className="p-1.5 hover:bg-gray-700 rounded-lg transition-colors"
                title="Clear conversation"
              >
                <RotateCcw className="w-4 h-4 text-gray-400" />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center space-y-4">
            <div className={`p-4 bg-${config.color}-500/10 rounded-full`}>
              <Icon className={`w-8 h-8 text-${config.color}-400`} />
            </div>
            <div>
              <h4 className="text-white font-medium mb-1">Start a conversation</h4>
              <p className="text-sm text-gray-400">Try one of these questions:</p>
            </div>
            <div className="grid grid-cols-1 gap-2 w-full max-w-md">
              {config.suggestions.map((suggestion, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSuggestion(suggestion)}
                  className="px-3 py-2 bg-gray-700/50 hover:bg-gray-700 border border-gray-600 rounded-lg text-left text-sm text-gray-300 transition-colors"
                >
                  <Zap className="w-3 h-3 inline mr-1.5 text-blue-400" />
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((message, idx) => (
            <div
              key={idx}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[80%] rounded-lg px-4 py-2.5 ${
                  message.role === 'user'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-700/50 border border-gray-600 text-gray-200'
                }`}
              >
                <div className="text-sm whitespace-pre-wrap font-mono leading-relaxed">
                  {message.content}
                </div>
                <div className="text-xs opacity-60 mt-1">
                  {message.timestamp.toLocaleTimeString()}
                </div>
              </div>
            </div>
          ))
        )}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-700/50 border border-gray-600 rounded-lg px-4 py-2.5">
              <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />
            </div>
          </div>
        )}
      </div>

      {/* Input Area */}
      <form onSubmit={handleSubmit} className="p-3 border-t border-gray-700 bg-gray-900/50">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={config.placeholder}
            className="flex-1 px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 text-sm"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={!input.trim() || loading}
            className={`px-4 py-2 bg-${config.color}-600 hover:bg-${config.color}-700 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded-lg transition-colors flex items-center gap-2 text-sm font-medium`}
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <>
                <Send className="w-4 h-4" />
                Send
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
