import React, { useState, useEffect, useRef } from 'react';
import { Bot, Send, X, RefreshCw, Sparkles, Cpu, ChevronRight } from 'lucide-react';
import { sendChatMessage, ChatMessage } from '../services/chatService';
import { useMapStore } from '../store/mapStore';
import { useHotspotsQuery } from '../services/queries/useHotspotsQuery';
import { getStoredUser, getStoredToken } from '../services/authService';
import { AuthModal } from './AuthModal';

const GUEST_AI_HOTSPOT_LIMIT = 5;

interface ChatAssistantProps {
  selectedHotspotId?: string | null;
  positionClass?: string;
}

export const ChatAssistant: React.FC<ChatAssistantProps> = ({
  selectedHotspotId,
  positionClass = 'absolute bottom-3 right-3 z-30',
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [isAuthGateOpen, setIsAuthGateOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      content: 'Hello! I am the ThermalTrace AI Intelligence Assistant. Ask me about active thermal anomalies, industrial thermal source predictions, facility proximity, or historical trends across India.'
    }
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | undefined>(undefined);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const selectedDate = useMapStore((s) => s.selectedDate);
  const { data: hotspots } = useHotspotsQuery(selectedDate);
  const activeHotspotsCount = hotspots?.length ?? 0;

  const isUserAuthenticated = (): boolean => {
    return Boolean(getStoredUser() || getStoredToken());
  };

  const checkGuestGate = (): boolean => {
    if (!isUserAuthenticated() && activeHotspotsCount > GUEST_AI_HOTSPOT_LIMIT) {
      setIsAuthGateOpen(true);
      return false; // STOP! No Gemini API request!
    }
    return true;
  };

  const handleOpenChat = () => {
    if (checkGuestGate()) {
      setIsOpen(true);
    }
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  // Handle external trigger for selected hotspot
  useEffect(() => {
    const handleAskHotspot = (e: CustomEvent<{ hotspotId: string }>) => {
      if (checkGuestGate()) {
        setIsOpen(true);
        const prompt = `Explain hotspot ${e.detail.hotspotId}. What is its ML classification prediction, FRP, confidence, persistence, and facility context?`;
        setInputMessage(prompt);
      }
    };

    window.addEventListener('ask-ai-hotspot' as any, handleAskHotspot as any);
    return () => {
      window.removeEventListener('ask-ai-hotspot' as any, handleAskHotspot as any);
    };
  }, [activeHotspotsCount]);

  const handleSend = async (customPrompt?: string) => {
    const textToSend = customPrompt || inputMessage;
    if (!textToSend.trim() || loading) return;

    if (!checkGuestGate()) return;

    const newHistory: ChatMessage[] = [...messages, { role: 'user', content: textToSend }];
    setMessages(newHistory);
    if (!customPrompt) setInputMessage('');
    setLoading(true);

    try {
      const res = await sendChatMessage(textToSend, conversationId, newHistory);
      setConversationId(res.conversationId);
      setMessages([...newHistory, { role: 'assistant', content: res.message }]);

      if (res.action) {
        if (res.action.type === 'focus_hotspot' && res.action.targetId) {
          window.dispatchEvent(new CustomEvent('map-focus-hotspot', { detail: { hotspotId: res.action.targetId } }));
        } else if (res.action.type === 'apply_filter' && res.action.classification) {
          window.dispatchEvent(new CustomEvent('map-filter-classification', { detail: { classification: res.action.classification } }));
        }
      }
    } catch (err: any) {
      setMessages([
        ...newHistory,
        {
          role: 'assistant',
          content: 'An error occurred while connecting to the LLM assistant service. Please check your backend connection.'
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setConversationId(undefined);
    setMessages([
      {
        role: 'assistant',
        content: 'Conversation reset. How can I assist you with ThermalTrace telemetry today?'
      }
    ]);
  };

  return (
    <>
      {/* Compact Floating Launcher Button */}
      {!isOpen && (
        <button
          onClick={handleOpenChat}
          className={`${positionClass} flex items-center gap-1.5 px-3 py-2 bg-gradient-to-r from-amber-500 to-red-600 hover:from-amber-600 hover:to-red-700 text-white rounded-full shadow-xl hover:shadow-2xl transition-all duration-300 transform hover:scale-105 font-bold text-xs border border-amber-400/30 cursor-pointer select-none`}
          title="Open ThermalTrace AI Assistant"
        >
          <Bot className="w-4 h-4 animate-pulse shrink-0 text-amber-100" />
          <span className="tracking-wide text-xs">AI</span>
          <Sparkles className="w-3.5 h-3.5 text-amber-200 shrink-0" />
        </button>
      )}

      {/* Auth Gate Modal when Guest > 5 hotspots */}
      <AuthModal
        isOpen={isAuthGateOpen}
        initialMode="login"
        notice="Login or signup to explore more of ThermalTrace."
        onClose={() => setIsAuthGateOpen(false)}
        onSuccess={() => {
          setIsAuthGateOpen(false);
          setIsOpen(true);
        }}
      />

      {/* Floating Chat Drawer */}
      {isOpen && (
        <div className="fixed bottom-3 right-3 sm:bottom-6 sm:right-6 z-50 w-[calc(100vw-1.5rem)] sm:w-[420px] max-w-[420px] h-[calc(100vh-5rem)] sm:h-[560px] max-h-[560px] bg-slate-950/95 backdrop-blur-xl border border-slate-800 rounded-2xl shadow-2xl flex flex-col overflow-hidden transition-all duration-300">
          {/* Header */}
          <div className="px-4 py-3.5 bg-slate-900/80 border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="p-2 bg-gradient-to-br from-amber-500/20 to-red-500/20 rounded-lg border border-amber-500/30">
                <Bot className="w-4 h-4 text-amber-400" />
              </div>
              <div>
                <div className="text-sm font-semibold text-slate-100 flex items-center gap-1.5">
                  AI Intelligence Assistant
                  <span className="text-[10px] uppercase font-bold px-1.5 py-0.5 bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 rounded">
                    ONLINE
                  </span>
                </div>
                <div className="text-[11px] text-slate-400">Gemini Grounded Tool-Calling</div>
              </div>
            </div>

            <div className="flex items-center gap-1">
              <button
                onClick={handleClear}
                className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 rounded-md transition-colors"
                title="Reset Conversation"
              >
                <RefreshCw className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setIsOpen(false)}
                className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 rounded-md transition-colors"
                title="Close Drawer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Quick Hotspot Prompt Context (if selected) */}
          {selectedHotspotId && (
            <div className="px-3.5 py-2 bg-amber-950/30 border-b border-amber-500/20 flex items-center justify-between text-xs text-amber-300">
              <span className="truncate">Selected: {selectedHotspotId}</span>
              <button
                onClick={() => handleSend(`Explain hotspot ${selectedHotspotId}. What is its ML classification prediction, FRP, confidence, persistence, and facility context?`)}
                className="px-2 py-0.5 bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/40 rounded text-[11px] font-medium flex items-center gap-1 transition-colors"
              >
                Ask AI <ChevronRight className="w-3 h-3" />
              </button>
            </div>
          )}

          {/* Messages Feed */}
          <div className="flex-1 p-4 overflow-y-auto space-y-3.5 text-xs text-slate-200">
            {messages.map((msg, i) => (
              <div
                key={i}
                className={`flex gap-2.5 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {msg.role === 'assistant' && (
                  <div className="w-6 h-6 rounded-full bg-amber-500/20 border border-amber-500/30 flex items-center justify-center shrink-0 mt-0.5">
                    <Bot className="w-3.5 h-3.5 text-amber-400" />
                  </div>
                )}

                <div
                  className={`max-w-[82%] px-3.5 py-2.5 rounded-xl whitespace-pre-wrap leading-relaxed ${
                    msg.role === 'user'
                      ? 'bg-amber-600/90 text-white rounded-br-none'
                      : 'bg-slate-900/90 border border-slate-800 text-slate-200 rounded-bl-none shadow-sm'
                  }`}
                >
                  {msg.content}
                </div>
              </div>
            ))}

            {/* Tool Executing Activity Badge */}
            {loading && (
              <div className="flex items-center gap-2 text-[11px] text-amber-400 bg-amber-950/20 border border-amber-500/20 rounded-lg px-3 py-2 animate-pulse w-fit">
                <Cpu className="w-3.5 h-3.5 animate-spin" />
                <span>Executing backend tool calls & grounding response...</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="p-3 bg-slate-900/80 border-t border-slate-800">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSend();
              }}
              className="flex items-center gap-2"
            >
              <input
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                placeholder="Ask about thermal anomalies, facilities..."
                disabled={loading}
                className="flex-1 bg-slate-950 border border-slate-800 focus:border-amber-500/50 rounded-lg px-3 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none transition-colors"
              />
              <button
                type="submit"
                disabled={loading || !inputMessage.trim()}
                className="p-2 bg-amber-500 hover:bg-amber-600 disabled:opacity-50 text-slate-950 font-semibold rounded-lg transition-colors shrink-0"
              >
                <Send className="w-4 h-4" />
              </button>
            </form>
          </div>
        </div>
      )}
    </>
  );
};
