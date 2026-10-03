export const keys = {
  me: ["me"] as const,
  workspaces: ["workspaces"] as const,
  workspace: (ws: string) => ["workspaces", ws] as const,
  members: (ws: string) => ["workspaces", ws, "members"] as const,
  documents: (ws: string) => ["workspaces", ws, "documents"] as const,
  document: (id: string) => ["documents", id] as const,
  conversations: (ws: string) => ["workspaces", ws, "conversations"] as const,
  conversation: (id: string) => ["conversations", id] as const,
  retrieval: (messageId: string) => ["messages", messageId, "retrieval"] as const,
  analytics: (ws: string, days: number) => ["workspaces", ws, "analytics", days] as const,
  invite: (token: string) => ["invites", token] as const,
};
