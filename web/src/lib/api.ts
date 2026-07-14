export type Conversation = { id: string; title?: string; messages?: Message[] };
export type Message = { role: "user" | "assistant"; content: string };
export type StreamEvent = Record<string, unknown> & { type?: string; text?: string; answer?: string };

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { ...init, headers: { "Content-Type": "application/json", ...init?.headers } });
  if (!response.ok) throw new Error(response.status === 403 ? "仅允许本机访问" : "请求失败，请稍后重试");
  return response.json() as Promise<T>;
}
export const api = {
  listConversations: () => request<Conversation[]>("/api/conversations"),
  getConversation: (id: string) => request<Conversation>(`/api/conversations/${id}`),
  createConversation: () => request<Conversation>("/api/conversations", { method: "POST" }),
  deleteConversation: (id: string) => request<{ deleted: boolean }>(`/api/conversations/${id}`, { method: "DELETE" }),
  gameState: () => request<Record<string, unknown>>("/api/game-state"),
  readiness: () => request<Record<string, unknown>>("/health/ready"),
  admin: (name: string) => request<Record<string, unknown>>(`/admin/api/${name}`),
  adminAction: (name: string) => request<Record<string, unknown>>(`/admin/api/${name}`, { method: name === "health-check" ? "GET" : "POST" }),
  async streamChat(message: string, conversationId: string, onEvent: (event: StreamEvent) => void): Promise<void> {
    const response = await fetch("/api/chat/stream", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message, conversation_id: conversationId }) });
    if (!response.ok || !response.body) throw new Error("无法连接到 Pilot");
    const reader = response.body.getReader(); const decoder = new TextDecoder(); let buffer = "";
    while (true) {
      const { done, value } = await reader.read(); if (done) break;
      buffer += decoder.decode(value, { stream: true }); const lines = buffer.split("\n"); buffer = lines.pop() ?? "";
      for (const line of lines) if (line.startsWith("data: ") && line.slice(6) !== "[DONE]") onEvent(JSON.parse(line.slice(6)) as StreamEvent);
    }
  }
};
