export type MessageRole = "user" | "assistant";
export type ModelProvider = "openrouter" | "ollama";

export interface SourceChunk {
  id: string;
  text: string;
  score: number;
  dense_score?: number;
  bm25_score?: number;
  rerank_score?: number;
  document_id?: string;
  filename?: string;
  page?: number;
  chunk_id?: number;
  source_type?: string;
}

export interface DocumentMetadata {
  document_id: string;
  filename: string;
  uploaded_at: string;
  chunk_count: number;
  source_type: string;
  extraction?: {
    total_pages?: number;
    extracted_characters?: number;
    empty_pages?: number[];
    duplicate_lines_removed?: number;
    ocr_used?: boolean;
  };
}

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  sources?: SourceChunk[];
  thinking?: boolean;
  streaming?: boolean;
}

export interface ChatRequest {
  query: string;
  provider: ModelProvider;
  model: string;
  top_k: number;
  document_ids: string[];
  dense_weight: number;
  bm25_weight: number;
  candidate_pool_size: number;
  rerank: boolean;
  history: Array<{
    role: MessageRole;
    content: string;
  }>;
}

interface StreamCallbacks {
  request: ChatRequest;
  signal?: AbortSignal;
  onThinking?: () => void;
  onToken: (token: string) => void;
  onSources?: (sources: SourceChunk[]) => void;
  onDone?: () => void;
}

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export function getSessionId(): string {
  if (typeof window === "undefined") {
    return "default-session";
  }
  let id = localStorage.getItem("session_id");
  if (!id) {
    id = "session-" + Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
    localStorage.setItem("session_id", id);
  }
  return id;
}

async function getErrorMessage(response: Response, fallback: string) {
  try {
    const body = await response.json();
    if (typeof body.detail === "string") {
      return body.detail;
    }
    if (Array.isArray(body.detail) && body.detail.length > 0) {
      return body.detail
        .map((item: { msg?: string; message?: string }) => item?.msg ?? item?.message)
        .filter(Boolean)
        .join("; ");
    }
  } catch {
    // Keep the original fallback when the backend returns a non-JSON error.
  }

  return fallback;
}

export async function uploadPdf(file: File, chunkSize: number) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("chunk_size", String(chunkSize));

  const response = await fetch(`${API_BASE_URL}/upload`, {
    method: "POST",
    headers: {
      "X-Session-ID": getSessionId()
    },
    body: formData
  });

  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Upload failed"));
  }

  return response.json() as Promise<{
    document_id: string;
    filename: string;
    chunks_indexed: number;
    document: DocumentMetadata;
    documents: DocumentMetadata[];
    message: string;
  }>;
}

export async function getDocuments() {
  const response = await fetch(`${API_BASE_URL}/documents`, {
    headers: {
      "X-Session-ID": getSessionId()
    }
  });

  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Unable to load documents"));
  }

  return response.json() as Promise<{
    documents: DocumentMetadata[];
  }>;
}

export async function clearMemory(
  payload: { mode: "chat" } | { mode: "document"; document_id: string } | { mode: "all" } = { mode: "all" }
) {
  const response = await fetch(`${API_BASE_URL}/reset`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Session-ID": getSessionId()
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Unable to clear chat memory"));
  }

  return response.json() as Promise<{
    message: string;
    documents: DocumentMetadata[];
    vector_store: Record<string, unknown>;
  }>;
}

export async function streamChat({
  request,
  signal,
  onThinking,
  onToken,
  onSources,
  onDone
}: StreamCallbacks) {
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Session-ID": getSessionId()
    },
    body: JSON.stringify(request),
    signal
  });

  if (!response.ok || !response.body) {
    throw new Error(await getErrorMessage(response, "Unable to stream chat response"));
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (!line.trim()) {
        continue;
      }

      const event = JSON.parse(line) as
        | { type: "thinking" }
        | { type: "token"; token: string }
        | { type: "sources"; sources: SourceChunk[] }
        | { type: "done" };

      if (event.type === "thinking") {
        onThinking?.();
      }

      if (event.type === "token") {
        onToken(event.token);
      }

      if (event.type === "sources") {
        onSources?.(event.sources);
      }

      if (event.type === "done") {
        onDone?.();
      }
    }
  }
}

export interface CompareRequest {
  document_ids: string[];
  provider: ModelProvider;
  model: string;
  dense_weight: number;
  bm25_weight: number;
  candidate_pool_size: number;
}

interface CompareStreamCallbacks {
  request: CompareRequest;
  signal?: AbortSignal;
  onThinking?: () => void;
  onToken: (token: string) => void;
  onSources?: (sources: SourceChunk[]) => void;
  onDone?: () => void;
}

export async function streamCompare({
  request,
  signal,
  onThinking,
  onToken,
  onSources,
  onDone
}: CompareStreamCallbacks) {
  const response = await fetch(`${API_BASE_URL}/compare`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Session-ID": getSessionId()
    },
    body: JSON.stringify(request),
    signal
  });

  if (!response.ok || !response.body) {
    throw new Error(await getErrorMessage(response, "Unable to stream comparison response"));
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (!line.trim()) {
        continue;
      }

      const event = JSON.parse(line) as
        | { type: "thinking" }
        | { type: "token"; token: string }
        | { type: "sources"; sources: SourceChunk[] }
        | { type: "done" };

      if (event.type === "thinking") {
        onThinking?.();
      }

      if (event.type === "token") {
        onToken(event.token);
      }

      if (event.type === "sources") {
        onSources?.(event.sources);
      }

      if (event.type === "done") {
        onDone?.();
      }
    }
  }
}

export async function generatePpt(payload: {
  document_ids: string[];
  provider: ModelProvider;
  model: string;
}) {
  const response = await fetch(`${API_BASE_URL}/generate-ppt`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Session-ID": getSessionId()
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Presentation generation failed"));
  }

  const blob = await response.blob();
  const contentDisposition = response.headers.get("content-disposition");
  let filename = "presentation.pptx";
  if (contentDisposition) {
    const match = contentDisposition.match(/filename="?([^"]+)"?/);
    if (match && match[1]) {
      filename = match[1];
    }
  }

  return { blob, filename };
}
