/**
 * MaestraChat — Presentation component for Maestra conversations.
 *
 * Reads from and writes to the global MaestraChatProvider.
 * Holds only transient UI state (input text, streaming buffer, typing flag).
 *
 * Renders Markdown via react-markdown. No custom parser.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { Send, Loader2, RotateCcw } from 'lucide-react';
import Markdown from 'react-markdown';
import { useMaestraChat } from '../../contexts/MaestraChatContext';
import MAESTRA_PRESETS from './presets';

interface MaestraChatProps {
  module_context: string;
}

export default function MaestraChat({ module_context }: MaestraChatProps) {
  const { state, addMessage, setCurrentModule, clearSession } = useMaestraChat();

  // Transient UI state only — not persisted in global store
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamBuffer, setStreamBuffer] = useState('');
  const [isThinking, setIsThinking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Set module context on mount / module change
  useEffect(() => {
    setCurrentModule(module_context);
  }, [module_context, setCurrentModule]);

  // Auto-scroll as new content appears
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [state.messages, streamBuffer, isThinking]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // -------------------------------------------------------------------
  // Send message to Maestra backend via SSE
  // -------------------------------------------------------------------
  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || isStreaming) return;

      setError(null);
      const trimmed = text.trim();

      // Add user message to global store
      addMessage('user', trimmed, module_context);
      setInput('');
      setIsThinking(true);
      setIsStreaming(true);
      setStreamBuffer('');

      // Abort any in-flight request
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const response = await fetch('/api/maestra/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: trimmed,
            module_context,
            session_id: state.session_id,
          }),
          signal: controller.signal,
        });

        if (!response.ok) {
          const detail = await response.text().catch(() => response.statusText);
          throw new Error(
            `Maestra chat failed — POST /api/maestra/chat returned ${response.status}: ${detail}`,
          );
        }

        if (!response.body) {
          throw new Error(
            'Maestra chat failed — response body is null (streaming not supported by this environment)',
          );
        }

        // Read SSE stream
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let accumulated = '';
        let sseBuffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          sseBuffer += decoder.decode(value, { stream: true });

          // Parse SSE lines
          const lines = sseBuffer.split('\n');
          // Keep the last potentially incomplete line in the buffer
          sseBuffer = lines.pop() || '';

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue;
            const jsonStr = line.slice(6);
            if (!jsonStr) continue;

            try {
              const event = JSON.parse(jsonStr);

              if (event.type === 'content') {
                accumulated += event.text;
                setStreamBuffer(accumulated);
                setIsThinking(false);
              } else if (event.type === 'done') {
                // Streaming complete — commit to global store
                if (accumulated) {
                  addMessage('maestra', accumulated, module_context);
                }
                setStreamBuffer('');
                setIsStreaming(false);
                setIsThinking(false);
              }
            } catch {
              // Partial JSON line — will be completed on next chunk
            }
          }
        }

        // If stream ended without a done event, still commit what we have
        if (accumulated && isStreaming) {
          addMessage('maestra', accumulated, module_context);
          setStreamBuffer('');
          setIsStreaming(false);
          setIsThinking(false);
        }
      } catch (err: unknown) {
        if (err instanceof DOMException && err.name === 'AbortError') return;

        const message =
          err instanceof Error
            ? err.message
            : 'Maestra chat failed — unknown error';
        setError(message);
        setIsStreaming(false);
        setIsThinking(false);
        setStreamBuffer('');
      }
    },
    [addMessage, isStreaming, module_context, state.session_id],
  );

  // -------------------------------------------------------------------
  // Input handlers
  // -------------------------------------------------------------------
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(input);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  const handlePresetClick = (preset: string) => {
    sendMessage(preset);
  };

  // -------------------------------------------------------------------
  // Presets for current module
  // -------------------------------------------------------------------
  const presets = MAESTRA_PRESETS[module_context] || [];
  const showPresets = state.messages.length === 0 && !isStreaming;

  // -------------------------------------------------------------------
  // Module context label
  // -------------------------------------------------------------------
  const moduleLabel = module_context.toUpperCase();

  return (
    <div className="flex flex-col h-full bg-gray-900 border-l border-gray-700">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700 bg-gray-900">
        <div>
          <h2 className="text-sm font-semibold text-white tracking-wide">
            Maestra
            <span className="ml-2 text-xs font-normal text-gray-400">
              {moduleLabel}
            </span>
          </h2>
        </div>
        {state.messages.length > 0 && (
          <button
            onClick={clearSession}
            className="p-1.5 text-gray-400 hover:text-white hover:bg-gray-800 rounded transition-colors"
            title="Clear conversation"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4 min-h-0">
        {/* Presets — shown when conversation is empty */}
        {showPresets && (
          <div className="flex flex-col items-center justify-center h-full">
            <p className="text-sm text-gray-400 mb-4">Ask Maestra anything</p>
            <div className="flex flex-wrap gap-2 justify-center max-w-md">
              {presets.map((preset) => (
                <button
                  key={preset}
                  onClick={() => handlePresetClick(preset)}
                  className="px-3 py-1.5 text-xs text-gray-300 bg-gray-800 border border-gray-700 rounded-full hover:bg-gray-700 hover:border-gray-600 transition-colors text-left"
                >
                  {preset}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Message history from global store */}
        {state.messages.map((msg) => (
          <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
                msg.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-800 text-gray-200'
              }`}
            >
              {msg.role === 'maestra' ? (
                <div className="maestra-markdown prose prose-invert prose-sm max-w-none">
                  <Markdown>{msg.content}</Markdown>
                </div>
              ) : (
                <span className="whitespace-pre-wrap">{msg.content}</span>
              )}
              <div className="mt-1 text-[10px] text-gray-400 opacity-60">
                {new Date(msg.timestamp).toLocaleTimeString([], {
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </div>
            </div>
          </div>
        ))}

        {/* Thinking indicator */}
        {isThinking && (
          <div className="flex justify-start">
            <div className="bg-gray-800 rounded-lg px-3 py-2 text-sm text-gray-400">
              <span className="inline-flex items-center gap-1.5">
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                Maestra is thinking...
              </span>
            </div>
          </div>
        )}

        {/* Streaming buffer — live response being built */}
        {streamBuffer && !isThinking && (
          <div className="flex justify-start">
            <div className="max-w-[85%] bg-gray-800 rounded-lg px-3 py-2 text-sm text-gray-200">
              <div className="maestra-markdown prose prose-invert prose-sm max-w-none">
                <Markdown>{streamBuffer}</Markdown>
              </div>
            </div>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="flex justify-start">
            <div className="max-w-[85%] bg-red-900/30 border border-red-500/30 rounded-lg px-3 py-2 text-sm text-red-300">
              {error}
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="px-4 py-3 border-t border-gray-700">
        <div className="flex gap-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask Maestra..."
            rows={1}
            className="flex-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 resize-none"
            disabled={isStreaming}
          />
          <button
            type="submit"
            disabled={isStreaming || !input.trim()}
            className="px-3 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:cursor-not-allowed rounded-lg text-white transition-colors"
          >
            {isStreaming ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
