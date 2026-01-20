/**
 * Agent Chat Component
 *
 * Real-time chat interface for agent interactions:
 * - Message streaming via WebSocket
 * - Tool call visualization
 * - Approval request handling
 * - Cost and token tracking
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import {
  Send,
  Loader2,
  Bot,
  User,
  Wrench,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Clock,
  DollarSign,
  Zap,
  RefreshCw,
  Copy,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';

// Types
interface ToolCall {
  id: string;
  tool_name: string;
  tool_server: string;
  arguments: Record<string, any>;
  result?: any;
  status: 'pending' | 'running' | 'completed' | 'failed';
  duration_ms?: number;
}

interface ApprovalRequest {
  approval_id: string;
  action_type: string;
  action_details: Record<string, any>;
  expires_at: string;
}

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  tool_calls?: ToolCall[];
  approval_request?: ApprovalRequest;
  tokens_input?: number;
  tokens_output?: number;
  cost_usd?: number;
}

interface AgentRun {
  run_id: string;
  agent_id: string;
  agent_name: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'waiting_approval';
  started_at: Date;
  completed_at?: Date;
  messages: Message[];
  total_tokens_input: number;
  total_tokens_output: number;
  total_cost_usd: number;
  steps_executed: number;
}

interface AgentChatProps {
  agentId?: string;
  agentName?: string;
  onRunComplete?: (run: AgentRun) => void;
}

export default function AgentChat({
  agentId = 'default',
  agentName = 'AOS Agent',
  onRunComplete,
}: AgentChatProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [currentRun, setCurrentRun] = useState<AgentRun | null>(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [expandedToolCalls, setExpandedToolCalls] = useState<Set<string>>(new Set());

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // WebSocket connection for streaming
  const connectWebSocket = useCallback((runId: string) => {
    const token = localStorage.getItem('token');
    const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/v1/agents/runs/${runId}/stream`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setWsConnected(true);
      if (token) {
        ws.send(JSON.stringify({ type: 'auth', token }));
      }
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      handleStreamEvent(data);
    };

    ws.onclose = () => {
      setWsConnected(false);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setWsConnected(false);
    };

    return ws;
  }, []);

  // Handle streaming events
  const handleStreamEvent = useCallback((event: any) => {
    const { event: eventType, data } = event;

    switch (eventType) {
      case 'run_started':
        setCurrentRun((prev) => ({
          ...prev!,
          status: 'running',
        }));
        break;

      case 'step_started':
        // Update UI to show step progress
        break;

      case 'tool_call_started':
        setMessages((prev) => {
          const lastMsg = prev[prev.length - 1];
          if (lastMsg?.role === 'assistant') {
            const toolCall: ToolCall = {
              id: data.tool_call_id || crypto.randomUUID(),
              tool_name: data.tool_name,
              tool_server: data.tool_server,
              arguments: data.arguments,
              status: 'running',
            };
            return [
              ...prev.slice(0, -1),
              {
                ...lastMsg,
                tool_calls: [...(lastMsg.tool_calls || []), toolCall],
              },
            ];
          }
          return prev;
        });
        break;

      case 'tool_call_completed':
        setMessages((prev) => {
          const lastMsg = prev[prev.length - 1];
          if (lastMsg?.role === 'assistant' && lastMsg.tool_calls) {
            const toolCalls = lastMsg.tool_calls.map((tc) =>
              tc.tool_name === data.tool_name
                ? {
                    ...tc,
                    status: 'completed' as const,
                    result: data.result,
                    duration_ms: data.duration_ms,
                  }
                : tc
            );
            return [
              ...prev.slice(0, -1),
              { ...lastMsg, tool_calls: toolCalls },
            ];
          }
          return prev;
        });
        break;

      case 'approval_required':
        setCurrentRun((prev) => ({
          ...prev!,
          status: 'waiting_approval',
        }));
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: 'system',
            content: `Approval required for: ${data.action_type}`,
            timestamp: new Date(),
            approval_request: {
              approval_id: data.approval_id,
              action_type: data.action_type,
              action_details: data.action_details,
              expires_at: data.expires_at,
            },
          },
        ]);
        break;

      case 'run_completed':
        setCurrentRun((prev) => ({
          ...prev!,
          status: 'completed',
          completed_at: new Date(),
          total_tokens_input: data.tokens_input,
          total_tokens_output: data.tokens_output,
          total_cost_usd: data.cost_usd,
          steps_executed: data.steps_executed,
        }));
        setIsLoading(false);

        // Add final response
        if (data.output) {
          setMessages((prev) => [
            ...prev,
            {
              id: crypto.randomUUID(),
              role: 'assistant',
              content: data.output,
              timestamp: new Date(),
              tokens_input: data.tokens_input,
              tokens_output: data.tokens_output,
              cost_usd: data.cost_usd,
            },
          ]);
        }

        if (onRunComplete && currentRun) {
          onRunComplete({ ...currentRun, status: 'completed' });
        }
        break;

      case 'run_failed':
        setCurrentRun((prev) => ({
          ...prev!,
          status: 'failed',
          completed_at: new Date(),
        }));
        setIsLoading(false);
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: 'system',
            content: `Error: ${data.error}`,
            timestamp: new Date(),
          },
        ]);
        break;
    }
  }, [currentRun, onRunComplete]);

  // Submit message
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`/api/v1/agents/${agentId}/runs`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: token ? `Bearer ${token}` : '',
        },
        body: JSON.stringify({
          input: userMessage.content,
          stream: true,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to start agent run');
      }

      const data = await response.json();
      const runId = data.run_id;

      // Initialize current run
      setCurrentRun({
        run_id: runId,
        agent_id: agentId,
        agent_name: agentName,
        status: 'pending',
        started_at: new Date(),
        messages: [userMessage],
        total_tokens_input: 0,
        total_tokens_output: 0,
        total_cost_usd: 0,
        steps_executed: 0,
      });

      // Add assistant placeholder
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: '',
          timestamp: new Date(),
        },
      ]);

      // Connect to WebSocket for streaming
      connectWebSocket(runId);
    } catch (error) {
      setIsLoading(false);
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'system',
          content: `Error: ${error instanceof Error ? error.message : 'Unknown error'}`,
          timestamp: new Date(),
        },
      ]);
    }
  };

  // Handle approval decision
  const handleApproval = async (approvalId: string, approved: boolean, notes?: string) => {
    try {
      const token = localStorage.getItem('token');
      await fetch(`/api/v1/agents/approvals/${approvalId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: token ? `Bearer ${token}` : '',
        },
        body: JSON.stringify({ approved, notes }),
      });

      // Update message to show resolved
      setMessages((prev) =>
        prev.map((msg) =>
          msg.approval_request?.approval_id === approvalId
            ? {
                ...msg,
                content: `${msg.content} - ${approved ? 'APPROVED' : 'REJECTED'}`,
                approval_request: undefined,
              }
            : msg
        )
      );

      if (approved) {
        setCurrentRun((prev) => (prev ? { ...prev, status: 'running' } : null));
      }
    } catch (error) {
      console.error('Approval error:', error);
    }
  };

  // Toggle tool call expansion
  const toggleToolCall = (toolCallId: string) => {
    setExpandedToolCalls((prev) => {
      const next = new Set(prev);
      if (next.has(toolCallId)) {
        next.delete(toolCallId);
      } else {
        next.add(toolCallId);
      }
      return next;
    });
  };

  // Copy to clipboard
  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  // Render tool call
  const renderToolCall = (toolCall: ToolCall) => {
    const isExpanded = expandedToolCalls.has(toolCall.id);

    return (
      <div
        key={toolCall.id}
        className="bg-gray-900/50 rounded-lg border border-gray-700 overflow-hidden"
      >
        <button
          onClick={() => toggleToolCall(toolCall.id)}
          className="w-full flex items-center gap-3 px-3 py-2 hover:bg-gray-800/50 transition-colors"
        >
          {isExpanded ? (
            <ChevronDown className="w-4 h-4 text-gray-400" />
          ) : (
            <ChevronRight className="w-4 h-4 text-gray-400" />
          )}
          <Wrench className="w-4 h-4 text-cyan-400" />
          <span className="text-sm font-medium text-white">{toolCall.tool_name}</span>
          <span className="text-xs text-gray-500">({toolCall.tool_server})</span>
          <div className="flex-1" />
          {toolCall.status === 'running' && (
            <Loader2 className="w-4 h-4 text-yellow-400 animate-spin" />
          )}
          {toolCall.status === 'completed' && (
            <CheckCircle className="w-4 h-4 text-green-400" />
          )}
          {toolCall.status === 'failed' && (
            <XCircle className="w-4 h-4 text-red-400" />
          )}
          {toolCall.duration_ms !== undefined && (
            <span className="text-xs text-gray-500">{toolCall.duration_ms}ms</span>
          )}
        </button>

        {isExpanded && (
          <div className="px-3 py-2 border-t border-gray-700 space-y-2">
            <div>
              <div className="text-xs text-gray-400 mb-1">Arguments</div>
              <pre className="text-xs bg-gray-900 rounded p-2 overflow-x-auto text-gray-300">
                {JSON.stringify(toolCall.arguments, null, 2)}
              </pre>
            </div>
            {toolCall.result !== undefined && (
              <div>
                <div className="text-xs text-gray-400 mb-1">Result</div>
                <pre className="text-xs bg-gray-900 rounded p-2 overflow-x-auto text-gray-300 max-h-40">
                  {typeof toolCall.result === 'string'
                    ? toolCall.result
                    : JSON.stringify(toolCall.result, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  // Render approval request
  const renderApprovalRequest = (approval: ApprovalRequest) => (
    <div className="bg-yellow-900/30 border border-yellow-500/50 rounded-lg p-4">
      <div className="flex items-center gap-2 mb-3">
        <AlertTriangle className="w-5 h-5 text-yellow-400" />
        <span className="font-medium text-yellow-400">Approval Required</span>
      </div>
      <div className="space-y-2 mb-4">
        <div className="text-sm text-gray-300">
          <span className="text-gray-400">Action:</span> {approval.action_type}
        </div>
        <div className="text-xs bg-gray-900/50 rounded p-2 text-gray-400">
          {JSON.stringify(approval.action_details, null, 2)}
        </div>
        <div className="text-xs text-gray-500">
          Expires: {new Date(approval.expires_at).toLocaleString()}
        </div>
      </div>
      <div className="flex gap-2">
        <button
          onClick={() => handleApproval(approval.approval_id, true)}
          className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm font-medium transition-colors"
        >
          <CheckCircle className="w-4 h-4" />
          Approve
        </button>
        <button
          onClick={() => handleApproval(approval.approval_id, false)}
          className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium transition-colors"
        >
          <XCircle className="w-4 h-4" />
          Reject
        </button>
      </div>
    </div>
  );

  return (
    <div className="flex flex-col h-full bg-gray-800 rounded-lg border border-gray-700">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700 bg-gradient-to-r from-purple-900/50 to-blue-900/50">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-blue-500 rounded-lg flex items-center justify-center">
            <Bot className="w-6 h-6 text-white" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white">{agentName}</h2>
            <div className="flex items-center gap-2 text-xs">
              <span
                className={`px-2 py-0.5 rounded ${
                  wsConnected ? 'bg-green-500/20 text-green-400' : 'bg-gray-700 text-gray-400'
                }`}
              >
                {wsConnected ? 'Connected' : 'Disconnected'}
              </span>
              {currentRun && (
                <span
                  className={`px-2 py-0.5 rounded ${
                    currentRun.status === 'running'
                      ? 'bg-yellow-500/20 text-yellow-400'
                      : currentRun.status === 'completed'
                      ? 'bg-green-500/20 text-green-400'
                      : currentRun.status === 'failed'
                      ? 'bg-red-500/20 text-red-400'
                      : 'bg-gray-700 text-gray-400'
                  }`}
                >
                  {currentRun.status}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Run Stats */}
        {currentRun && (
          <div className="flex items-center gap-4 text-xs text-gray-400">
            <div className="flex items-center gap-1">
              <Zap className="w-3 h-3" />
              <span>{currentRun.total_tokens_input + currentRun.total_tokens_output} tokens</span>
            </div>
            <div className="flex items-center gap-1">
              <DollarSign className="w-3 h-3" />
              <span>${currentRun.total_cost_usd.toFixed(4)}</span>
            </div>
            <div className="flex items-center gap-1">
              <RefreshCw className="w-3 h-3" />
              <span>{currentRun.steps_executed} steps</span>
            </div>
          </div>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <Bot className="w-16 h-16 text-gray-600 mb-4" />
            <h3 className="text-lg font-medium text-gray-400 mb-2">Start a conversation</h3>
            <p className="text-sm text-gray-500 max-w-md">
              Ask questions about your data, request analyses, or trigger automated workflows.
              The agent will use available tools to help you.
            </p>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`flex gap-3 ${message.role === 'user' ? 'flex-row-reverse' : ''}`}
            >
              {/* Avatar */}
              <div
                className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                  message.role === 'user'
                    ? 'bg-blue-600'
                    : message.role === 'system'
                    ? 'bg-yellow-600'
                    : 'bg-purple-600'
                }`}
              >
                {message.role === 'user' ? (
                  <User className="w-4 h-4 text-white" />
                ) : message.role === 'system' ? (
                  <AlertTriangle className="w-4 h-4 text-white" />
                ) : (
                  <Bot className="w-4 h-4 text-white" />
                )}
              </div>

              {/* Content */}
              <div
                className={`flex-1 max-w-[80%] ${message.role === 'user' ? 'text-right' : ''}`}
              >
                <div
                  className={`inline-block rounded-lg px-4 py-3 ${
                    message.role === 'user'
                      ? 'bg-blue-600 text-white'
                      : message.role === 'system'
                      ? 'bg-yellow-900/30 border border-yellow-500/30 text-yellow-200'
                      : 'bg-gray-700 text-gray-200'
                  }`}
                >
                  {message.content && (
                    <div className="whitespace-pre-wrap text-sm">{message.content}</div>
                  )}

                  {/* Tool Calls */}
                  {message.tool_calls && message.tool_calls.length > 0 && (
                    <div className="mt-3 space-y-2">
                      {message.tool_calls.map(renderToolCall)}
                    </div>
                  )}

                  {/* Approval Request */}
                  {message.approval_request && renderApprovalRequest(message.approval_request)}

                  {/* Loading indicator for assistant */}
                  {message.role === 'assistant' &&
                    !message.content &&
                    !message.tool_calls?.length &&
                    isLoading && (
                      <div className="flex items-center gap-2">
                        <Loader2 className="w-4 h-4 animate-spin text-purple-400" />
                        <span className="text-sm text-gray-400">Thinking...</span>
                      </div>
                    )}
                </div>

                {/* Message metadata */}
                <div
                  className={`flex items-center gap-2 mt-1 text-xs text-gray-500 ${
                    message.role === 'user' ? 'justify-end' : ''
                  }`}
                >
                  <Clock className="w-3 h-3" />
                  <span>{message.timestamp.toLocaleTimeString()}</span>
                  {message.role === 'assistant' && message.cost_usd !== undefined && (
                    <>
                      <span className="text-gray-600">|</span>
                      <span>${message.cost_usd.toFixed(4)}</span>
                    </>
                  )}
                  {message.role !== 'user' && message.content && (
                    <button
                      onClick={() => copyToClipboard(message.content)}
                      className="p-1 hover:bg-gray-700 rounded transition-colors"
                      title="Copy to clipboard"
                    >
                      <Copy className="w-3 h-3" />
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-4 border-t border-gray-700">
        <div className="flex gap-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask the agent anything..."
            className="flex-1 px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="px-6 py-3 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-700 disabled:cursor-not-allowed rounded-lg text-white font-medium transition-colors flex items-center gap-2"
          >
            {isLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
