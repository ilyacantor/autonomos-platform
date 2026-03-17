/**
 * MaestraChatContext — Global chat store for Maestra conversations.
 *
 * Positioned ABOVE the page routing logic so that navigating between
 * module views (NLQ → AAM → DCL) does not destroy the conversation.
 */

import {
  createContext,
  useContext,
  useReducer,
  useCallback,
  ReactNode,
} from 'react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface MaestraMessage {
  id: string;
  role: 'user' | 'maestra';
  content: string;
  timestamp: number;
  module_context: string | null;
}

interface MaestraChatState {
  messages: MaestraMessage[];
  session_id: string;
  current_module: string | null;
}

interface MaestraChatContextType {
  state: MaestraChatState;
  addMessage: (role: 'user' | 'maestra', content: string, module_context: string | null) => void;
  getMessages: () => MaestraMessage[];
  clearSession: () => void;
  setCurrentModule: (module_context: string | null) => void;
}

// ---------------------------------------------------------------------------
// Reducer
// ---------------------------------------------------------------------------

type Action =
  | { type: 'ADD_MESSAGE'; role: 'user' | 'maestra'; content: string; module_context: string | null }
  | { type: 'CLEAR_SESSION' }
  | { type: 'SET_MODULE'; module_context: string | null };

function generateSessionId(): string {
  return `maestra-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

function chatReducer(state: MaestraChatState, action: Action): MaestraChatState {
  switch (action.type) {
    case 'ADD_MESSAGE':
      return {
        ...state,
        messages: [
          ...state.messages,
          {
            id: crypto.randomUUID(),
            role: action.role,
            content: action.content,
            timestamp: Date.now(),
            module_context: action.module_context,
          },
        ],
      };
    case 'CLEAR_SESSION':
      return {
        messages: [],
        session_id: generateSessionId(),
        current_module: state.current_module,
      };
    case 'SET_MODULE':
      return {
        ...state,
        current_module: action.module_context,
      };
    default:
      return state;
  }
}

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

const MaestraChatContext = createContext<MaestraChatContextType | undefined>(undefined);

const initialState: MaestraChatState = {
  messages: [],
  session_id: generateSessionId(),
  current_module: null,
};

export function MaestraChatProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(chatReducer, initialState);

  const addMessage = useCallback(
    (role: 'user' | 'maestra', content: string, module_context: string | null) => {
      dispatch({ type: 'ADD_MESSAGE', role, content, module_context });
    },
    [],
  );

  const getMessages = useCallback(() => state.messages, [state.messages]);

  const clearSession = useCallback(() => {
    dispatch({ type: 'CLEAR_SESSION' });
  }, []);

  const setCurrentModule = useCallback((module_context: string | null) => {
    dispatch({ type: 'SET_MODULE', module_context });
  }, []);

  return (
    <MaestraChatContext.Provider
      value={{ state, addMessage, getMessages, clearSession, setCurrentModule }}
    >
      {children}
    </MaestraChatContext.Provider>
  );
}

export function useMaestraChat() {
  const context = useContext(MaestraChatContext);
  if (context === undefined) {
    throw new Error('useMaestraChat must be used within a MaestraChatProvider');
  }
  return context;
}
