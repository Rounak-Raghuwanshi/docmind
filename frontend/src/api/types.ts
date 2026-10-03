export type Role = "owner" | "editor" | "viewer";
export type DocStatus = "queued" | "processing" | "ready" | "failed";

export interface User {
  id: string;
  email: string;
  full_name: string;
  is_guest: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  expires_in: number;
  user: User;
}

export interface Page<T> {
  items: T[];
  next_cursor: string | null;
}

export interface Workspace {
  id: string;
  name: string;
  role: Role;
  is_personal: boolean;
  is_demo: boolean;
  document_count: number;
  member_count: number;
  created_at: string;
}

export interface Member {
  user_id: string;
  email: string;
  full_name: string;
  role: Role;
  joined_at: string;
}

export interface Invite {
  token: string;
  url: string;
  role: Role;
  expires_at: string;
}

export interface InvitePreview {
  workspace_id: string;
  workspace_name: string;
  role: Role;
  invited_by: string;
  expires_at: string;
}

export interface DocumentItem {
  id: string;
  workspace_id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  status: DocStatus;
  pages_total: number | null;
  pages_done: number;
  chunk_count: number;
  error_message: string | null;
  summary: string | null;
  suggested_questions: string[] | null;
  embedding_model: string | null;
  created_at: string;
  processed_at: string | null;
}

export interface DocumentEvent {
  document_id: string;
  status: DocStatus;
  pages_done: number;
  pages_total: number | null;
  error_message: string | null;
  stage: "parsing" | "embedding" | "retrying" | null;
}

export interface Citation {
  n: number;
  chunk_id: string;
  document_id: string;
  filename: string;
  page: number;
  page_end?: number | null;
  snippet: string;
}

export interface Conversation {
  id: string;
  workspace_id: string;
  title: string;
  document_filter: string[] | null;
  created_at: string;
  updated_at: string;
}

export type MessageStatus = "complete" | "stopped" | "error" | "streaming";

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations: Citation[];
  status: MessageStatus;
  not_found: boolean;
  cached: boolean;
  model: string | null;
  first_token_ms: number | null;
  total_ms: number | null;
  feedback: 1 | -1 | null;
  created_at: string;
}

export interface ConversationDetail extends Conversation {
  messages: Message[];
}

export interface RetrievedChunk {
  chunk_id: string;
  document_id: string;
  filename: string;
  page_start: number;
  page_end: number;
  context: string;
  content: string;
  vector_rank: number | null;
  vector_score: number | null;
  keyword_rank: number | null;
  keyword_score: number | null;
  rrf_score: number | null;
  rerank_score: number | null;
}

export interface RetrievalDebug {
  message_id: string;
  rewritten_question: string | null;
  retrieval_ms: number | null;
  rerank_ms: number | null;
  chunks: RetrievedChunk[];
}

export interface Analytics {
  days: number;
  total_questions: number;
  avg_total_ms: number | null;
  avg_first_token_ms: number | null;
  not_found_rate: number | null;
  cache_hit_rate: number | null;
  feedback_up: number;
  feedback_down: number;
  feedback_score: number | null;
  daily: {
    day: string;
    questions: number;
    avg_total_ms: number | null;
    avg_first_token_ms: number | null;
    not_found: number;
  }[];
  top_documents: { document_id: string; filename: string; citations: number }[];
}

export interface EmbeddingPoint {
  chunk_id: string;
  document_id: string;
  filename: string;
  page: number;
  preview: string;
  x: number;
  y: number;
  z: number;
}

export interface Insights {
  days: number;
  points: EmbeddingPoint[];
  explained_variance: number[];
  retrieval_sources: { both: number; vector_only: number; keyword_only: number };
  confidence: { start: number; end: number; answered: number; not_found: number }[];
  relevance_threshold: number;
  knowledge_gaps: { question: string; count: number }[];
  coverage: {
    document_id: string;
    filename: string;
    chunks: number;
    pages: number | null;
    answers: number;
  }[];
  highlights: string[];
}
