/**
 * Chat Service client for ThermalTrace AI Intelligence Assistant.
 */
import api from './api';

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface ToolCallItem {
  name: string;
  args?: Record<string, any>;
  result?: any;
}

export interface ChatResponse {
  message: string;
  conversationId: string;
  toolCalls: ToolCallItem[];
  action?: Record<string, any>;
  metadata: Record<string, any>;
}

export const sendChatMessage = async (
  message: string,
  conversationId?: string,
  history?: ChatMessage[]
): Promise<ChatResponse> => {
  const response = await api.post<ChatResponse>('/api/v1/chat', {
    message,
    conversationId,
    history,
  });
  return response.data;
};
