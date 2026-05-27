"use client";

import { useEffect, useRef, useState } from "react";
import { FileText, GitCompare, Menu, PenSquare, Presentation, Sparkles, Trash2, X } from "lucide-react";
import {
  ChatMessage,
  DocumentMetadata,
  ModelProvider,
  clearMemory,
  generatePpt,
  getDocuments,
  streamChat,
  streamCompare,
  uploadPdf
} from "@/lib/api";
import { InputBar } from "./InputBar";
import { MessageBubble } from "./MessageBubble";
import { QueryMode, Sidebar } from "./Sidebar";

const APP_TITLE = "Multimodal AI Research Assistant";
const THINKING_TITLE = "Thinking...";
const MAX_PDF_UPLOAD_BYTES = 15 * 1024 * 1024;

const GREETINGS = [
  "What research question are we solving today?",
  "Ready to explore some papers?",
  "What would you like to analyze today?"
];

const DEFAULT_MODELS: Record<ModelProvider, string[]> = {
  openrouter: [
    "openai/gpt-4o-mini",
    "anthropic/claude-3.5-sonnet",
    "google/gemini-2.0-flash-001",
    "meta-llama/llama-3.1-8b-instruct"
  ],
  ollama: ["llama3.1:8b", "mistral:7b", "phi4-mini", "qwen2.5:7b"]
};

function createId() {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function formatProviderLabel(provider: ModelProvider) {
  return provider === "openrouter" ? "OpenRouter" : "Ollama";
}

function formatModelLabel(model: string) {
  if (model === "openai/gpt-4o-mini") {
    return "GPT-4o mini";
  }

  if (model === "anthropic/claude-3.5-sonnet") {
    return "Claude 3.5 Sonnet";
  }

  if (model === "google/gemini-2.0-flash-001") {
    return "Gemini 2.0 Flash";
  }

  if (model === "meta-llama/llama-3.1-8b-instruct") {
    return "Llama 3.1 8B";
  }

  return model;
}

export function ChatWindow() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isResetting, setIsResetting] = useState(false);
  const [isClearingPdf, setIsClearingPdf] = useState(false);
  const [isGeneratingPpt, setIsGeneratingPpt] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(true);
  const [provider, setProvider] = useState<ModelProvider>("openrouter");
  const [model, setModel] = useState(DEFAULT_MODELS.openrouter[0]);
  const [chunkSize, setChunkSize] = useState(700);
  const [topK, setTopK] = useState(4);
  const [denseWeight, setDenseWeight] = useState(0.72);
  const [bm25Weight, setBm25Weight] = useState(0.28);
  const [candidatePoolSize, setCandidatePoolSize] = useState(24);
  const [uploadLabel, setUploadLabel] = useState<string | null>(null);
  const [documents, setDocuments] = useState<DocumentMetadata[]>([]);
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<string[]>([]);
  const [currentDocumentId, setCurrentDocumentId] = useState<string | null>(null);
  const [queryMode, setQueryMode] = useState<QueryMode>("current");
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const [greeting, setGreeting] = useState(GREETINGS[0]);

  useEffect(() => {
    setGreeting(GREETINGS[Math.floor(Math.random() * GREETINGS.length)]);
  }, []);

  useEffect(() => {
    document.title = isSending ? THINKING_TITLE : APP_TITLE;
    return () => {
      document.title = APP_TITLE;
    };
  }, [isSending]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, isSending]);

  useEffect(() => {
    getDocuments()
      .then((payload) => {
        setDocuments(payload.documents);
        setCurrentDocumentId((current) =>
          current && payload.documents.some((document) => document.document_id === current)
            ? current
            : payload.documents[0]?.document_id ?? null
        );
        setSelectedDocumentIds((current) =>
          current.filter((documentId) =>
            payload.documents.some((document) => document.document_id === documentId)
          )
        );
      })
      .catch(() => {
        setDocuments([]);
      });
  }, []);

  const handleProviderChange = (nextProvider: ModelProvider) => {
    setProvider(nextProvider);
    setModel(DEFAULT_MODELS[nextProvider][0]);
  };

  const handleReset = async () => {
    if (isResetting || isSending || isUploading || isClearingPdf) {
      return;
    }

    setIsResetting(true);
    try {
      const payload = await clearMemory({ mode: "chat" });
      setDocuments(payload.documents);
      setMessages([]);
      setInput("");
      setUploadLabel("Chat memory cleared");
    } catch (error) {
      setUploadLabel(
        error instanceof Error ? error.message : "Unable to clear chat memory"
      );
    } finally {
      setIsResetting(false);
    }
  };

  const handleClearPdf = async () => {
    if (selectedDocumentIds.length === 0 || isClearingPdf || isSending || isUploading || isResetting) {
      return;
    }

    setIsClearingPdf(true);
    try {
      for (const documentId of selectedDocumentIds) {
        await clearMemory({ mode: "document", document_id: documentId });
      }
      const payload = await getDocuments();
      setDocuments(payload.documents);
      setCurrentDocumentId((current) =>
        current && payload.documents.some((document) => document.document_id === current)
          ? current
          : payload.documents[0]?.document_id ?? null
      );
      setSelectedDocumentIds([]);
      setUploadLabel("Selected PDF context cleared");
    } catch (error) {
      setUploadLabel(
        error instanceof Error ? error.message : "Unable to clear PDF context"
      );
    } finally {
      setIsClearingPdf(false);
    }
  };

  const sendMessage = async (messageText: string) => {
    const trimmed = messageText.trim();
    if (!trimmed || isSending) {
      return;
    }

    const requestDocumentIds =
      queryMode === "all"
        ? []
        : queryMode === "current"
          ? currentDocumentId
            ? [currentDocumentId]
            : []
          : selectedDocumentIds;

    if (queryMode === "selected" && requestDocumentIds.length === 0) {
      setUploadLabel("Select at least one document to query");
      return;
    }

    const userMessage: ChatMessage = {
      id: createId(),
      role: "user",
      content: trimmed
    };

    const assistantMessage: ChatMessage = {
      id: createId(),
      role: "assistant",
      content: "",
      thinking: true,
      streaming: false,
      sources: []
    };

    const history = messages.map((item) => ({
      role: item.role,
      content: item.content
    }));

    setMessages((current) => [...current, userMessage, assistantMessage]);
    setInput("");
    setIsSending(true);

    try {
      await streamChat({
        request: {
          query: trimmed,
          provider,
          model,
          top_k: topK,
          document_ids: requestDocumentIds,
          dense_weight: denseWeight,
          bm25_weight: bm25Weight,
          candidate_pool_size: candidatePoolSize,
          rerank: false,
          history
        },
        onThinking: () => {
          setMessages((current) =>
            current.map((item) =>
              item.id === assistantMessage.id
                ? { ...item, thinking: true, streaming: false }
                : item
            )
          );
        },
        onToken: (token) => {
          setMessages((current) =>
            current.map((item) =>
              item.id === assistantMessage.id
                ? {
                    ...item,
                    content: `${item.content}${token}`,
                    thinking: false,
                    streaming: true
                  }
                : item
            )
          );
        },
        onSources: (sources) => {
          setMessages((current) =>
            current.map((item) =>
              item.id === assistantMessage.id ? { ...item, sources } : item
            )
          );
        },
        onDone: () => {
          setMessages((current) =>
            current.map((item) =>
              item.id === assistantMessage.id
                ? { ...item, thinking: false, streaming: false }
                : item
            )
          );
        }
      });
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "The backend did not return a valid response.";

      setMessages((current) =>
        current.map((item) =>
          item.id === assistantMessage.id
            ? {
                ...item,
                content: `I could not complete that request. ${message}`,
                thinking: false,
                streaming: false
              }
            : item
        )
      );
    } finally {
      setIsSending(false);
    }
  };

  const handleCompareSelected = async () => {
    if (selectedDocumentIds.length < 2 || isSending || isUploading || isResetting || isClearingPdf) {
      return;
    }

    const selectedDocs = documents.filter((doc) => selectedDocumentIds.includes(doc.document_id));
    const filenames = selectedDocs.map((doc) => doc.filename).join(", ");

    const userMessage: ChatMessage = {
      id: createId(),
      role: "user",
      content: `Generate structured comparative analysis for selected papers: ${filenames}`
    };

    const assistantMessage: ChatMessage = {
      id: createId(),
      role: "assistant",
      content: "",
      thinking: true,
      streaming: false,
      sources: []
    };

    setMessages((current) => [...current, userMessage, assistantMessage]);
    setIsSending(true);

    try {
      await streamCompare({
        request: {
          document_ids: selectedDocumentIds,
          provider,
          model,
          dense_weight: denseWeight,
          bm25_weight: bm25Weight,
          candidate_pool_size: candidatePoolSize
        },
        onThinking: () => {
          setMessages((current) =>
            current.map((item) =>
              item.id === assistantMessage.id
                ? { ...item, thinking: true, streaming: false }
                : item
            )
          );
        },
        onToken: (token) => {
          setMessages((current) =>
            current.map((item) =>
              item.id === assistantMessage.id
                ? {
                    ...item,
                    content: `${item.content}${token}`,
                    thinking: false,
                    streaming: true
                  }
                : item
            )
          );
        },
        onSources: (sources) => {
          setMessages((current) =>
            current.map((item) =>
              item.id === assistantMessage.id ? { ...item, sources } : item
            )
          );
        },
        onDone: () => {
          setMessages((current) =>
            current.map((item) =>
              item.id === assistantMessage.id
                ? { ...item, thinking: false, streaming: false }
                : item
            )
          );
        }
      });
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "The backend did not return a valid response.";

      setMessages((current) =>
        current.map((item) =>
          item.id === assistantMessage.id
            ? {
                ...item,
                content: `I could not complete that request. ${message}`,
                thinking: false,
                streaming: false
              }
            : item
        )
      );
    } finally {
      setIsSending(false);
    }
  };

  const handleGeneratePpt = async () => {
    const requestDocumentIds =
      queryMode === "all"
        ? documents.map((d) => d.document_id)
        : queryMode === "current"
          ? currentDocumentId
            ? [currentDocumentId]
            : []
          : selectedDocumentIds;

    if (requestDocumentIds.length === 0) {
      setUploadLabel("Select at least one document to generate slides");
      return;
    }

    setIsGeneratingPpt(true);
    setUploadLabel("Summarizing paper & building slide deck...");

    try {
      const { blob, filename } = await generatePpt({
        document_ids: requestDocumentIds,
        provider,
        model
      });

      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", filename);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      setUploadLabel("Presentation slide deck downloaded successfully!");
    } catch (error) {
      setUploadLabel(
        error instanceof Error ? error.message : "Failed to generate presentation"
      );
    } finally {
      setIsGeneratingPpt(false);
    }
  };


  const handleUpload = async (file: File) => {
    if (isSending || isResetting || isClearingPdf) {
      return;
    }

    if (file.type && file.type !== "application/pdf") {
      setUploadLabel("Only PDF uploads are supported");
      return;
    }

    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setUploadLabel("Only PDF uploads are supported");
      return;
    }

    if (file.size > MAX_PDF_UPLOAD_BYTES) {
      setUploadLabel("PDF is too large. Maximum upload size is 15 MB.");
      return;
    }

    setIsUploading(true);
    try {
      const payload = await uploadPdf(file, chunkSize);
      setDocuments(payload.documents);
      setCurrentDocumentId(payload.document_id);
      setQueryMode("current");
      setSelectedDocumentIds((current) => [...new Set([...current, payload.document_id])]);
      setUploadLabel("PDF ready for analysis");
    } catch (error) {
      setUploadLabel(
        error instanceof Error ? error.message : "PDF upload failed"
      );
    } finally {
      setIsUploading(false);
    }
  };

  const hasMessages = messages.length > 0;
  const modelBadge = `${formatModelLabel(model)} | ${formatProviderLabel(provider)}`;
  const selectedDocuments = documents.filter((document) =>
    selectedDocumentIds.includes(document.document_id)
  );
  const currentDocument = documents.find((document) => document.document_id === currentDocumentId);
  const documentBadge =
    queryMode === "all" && documents.length > 0
      ? `All documents (${documents.length})`
      : queryMode === "current" && currentDocument
        ? currentDocument.filename
        : selectedDocuments.length === 0
      ? null
      : selectedDocuments.length === 1
        ? selectedDocuments[0].filename
        : `${selectedDocuments.length} documents selected`;

  return (
    <div className="flex h-screen overflow-hidden bg-transparent text-white">
      <Sidebar
        provider={provider}
        model={model}
        models={DEFAULT_MODELS[provider]}
        chunkSize={chunkSize}
        topK={topK}
        denseWeight={denseWeight}
        bm25Weight={bm25Weight}
        candidatePoolSize={candidatePoolSize}
        documents={documents}
        selectedDocumentIds={selectedDocumentIds}
        queryMode={queryMode}
        isOpen={isSidebarOpen}
        isCollapsed={isSidebarCollapsed}
        onClose={() => setIsSidebarOpen(false)}
        onToggleCollapse={() => setIsSidebarCollapsed((current) => !current)}
        onProviderChange={handleProviderChange}
        onModelChange={setModel}
        onChunkSizeChange={setChunkSize}
        onTopKChange={setTopK}
        onDenseWeightChange={setDenseWeight}
        onBm25WeightChange={setBm25Weight}
        onCandidatePoolSizeChange={setCandidatePoolSize}
        onDocumentSelectionChange={setSelectedDocumentIds}
        onQueryModeChange={setQueryMode}
      />

      <main className="relative flex min-w-0 flex-1 flex-col overflow-hidden">
        <header className="sticky top-0 z-20 flex h-14 shrink-0 items-center justify-between border-b border-white/8 bg-[#09090bf2] px-3 backdrop-blur-xl sm:px-6 lg:px-8">
          <div className="flex min-w-0 items-center gap-3">
            <button
              type="button"
              aria-label="Open controls"
              className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-white/10 bg-white/5 text-white/80 transition hover:bg-white/10 lg:hidden"
              onClick={() => setIsSidebarOpen(true)}
            >
              <Menu className="h-4.5 w-4.5" />
            </button>

            <div className="min-w-0">
              <div className="truncate text-sm font-medium text-slate-100 sm:text-[15px]">
                {APP_TITLE}
              </div>
            </div>
          </div>

          <div className="ml-3 flex items-center gap-2">
            {documentBadge ? (
              <div className="hidden max-w-[240px] items-center gap-2 rounded-full border border-emerald-400/15 bg-emerald-400/10 px-3 py-1.5 text-[11px] text-emerald-200 sm:inline-flex sm:text-xs">
                <FileText className="h-3.5 w-3.5 shrink-0" />
                <span className="truncate">{documentBadge}</span>
                <button
                  type="button"
                  className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-white/10 text-emerald-100 transition hover:bg-white/20"
                  onClick={handleClearPdf}
                  aria-label="Delete current document"
                  disabled={isClearingPdf || isSending || isUploading || isResetting}
                >
                  <X className="h-3 w-3" />
                </button>
              </div>
            ) : null}

            <button
              type="button"
              className="inline-flex h-8 items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 text-[11px] text-slate-200 transition hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-50 sm:text-xs"
              onClick={handleReset}
              disabled={isResetting || isSending || isUploading || isClearingPdf}
            >
              <PenSquare className="h-3.5 w-3.5" />
              {isResetting ? "Clearing..." : "New chat"}
            </button>

            {selectedDocumentIds.length >= 2 ? (
              <button
                type="button"
                className="inline-flex h-8 items-center gap-2 rounded-full border border-accent/20 bg-accent/15 px-3 text-[11px] text-accent transition hover:bg-accent/25 disabled:cursor-not-allowed disabled:opacity-50 sm:text-xs"
                onClick={handleCompareSelected}
                disabled={isSending || isUploading || isResetting || isClearingPdf}
              >
                <GitCompare className="h-3.5 w-3.5" />
                Compare Papers
              </button>
            ) : null}

            {documents.length > 0 ? (
              <button
                type="button"
                className="inline-flex h-8 items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 text-[11px] text-slate-200 transition hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-50 sm:text-xs"
                onClick={handleGeneratePpt}
                disabled={isGeneratingPpt || isSending || isUploading || isResetting || isClearingPdf}
              >
                <Presentation className="h-3.5 w-3.5 text-accent" />
                {isGeneratingPpt ? "Generating PPT..." : "Generate PPT"}
              </button>
            ) : null}

            <button
              type="button"
              className="hidden h-8 items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 text-[11px] text-slate-200 transition hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-50 sm:inline-flex sm:text-xs"
              onClick={handleClearPdf}
              disabled={selectedDocumentIds.length === 0 || isClearingPdf || isSending || isUploading || isResetting}
            >
              <Trash2 className="h-3.5 w-3.5" />
              {isClearingPdf ? "Removing..." : "Clear PDF"}
            </button>

            <div className="hidden max-w-[56vw] items-center gap-2 rounded-full border border-white/10 bg-black/20 px-3 py-1.5 text-[11px] text-white/70 sm:inline-flex sm:max-w-none sm:text-xs">
              <Sparkles className="h-3.5 w-3.5 shrink-0 text-accent" />
              <span className="truncate">{modelBadge}</span>
            </div>
          </div>
        </header>

        <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
          <section className="scrollbar-thin flex-1 overflow-y-auto px-3 sm:px-6 lg:px-8">
            <div className="mx-auto flex min-h-full w-full max-w-[720px] flex-col pb-6 pt-4 sm:pb-8 sm:pt-6">
              <div
                className={[
                  "mx-auto flex w-full max-w-[720px] flex-col items-center justify-center text-center transition-all duration-500",
                  hasMessages
                    ? "pointer-events-none max-h-0 -translate-y-6 overflow-hidden opacity-0"
                    : "max-h-[420px] min-h-[28vh] translate-y-0 opacity-100 sm:max-h-[440px] sm:min-h-[34vh]"
                ].join(" ")}
              >
                <h1 className="max-w-3xl text-3xl font-semibold tracking-tight text-white sm:text-5xl lg:text-6xl">
                  {greeting}
                </h1>
                <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-400 sm:mt-5 sm:text-lg sm:leading-8">
                  Upload a PDF, tune retrieval, and stream grounded answers in a clean research conversation.
                </p>
                {documents.length >= 2 ? (
                  <div className="mt-6 flex flex-col items-center gap-3">
                    <p className="text-xs text-slate-500">
                      You have {documents.length} papers uploaded. Ready to compare them?
                    </p>
                    <button
                      type="button"
                      className="inline-flex h-10 items-center gap-2 rounded-full border border-accent/20 bg-accent/10 px-4 text-xs font-medium text-accent transition hover:bg-accent/20"
                      onClick={() => {
                        if (selectedDocumentIds.length < 2) {
                          setSelectedDocumentIds(documents.map((d) => d.document_id));
                        }
                        handleCompareSelected();
                      }}
                      disabled={isSending}
                    >
                      <GitCompare className="h-4 w-4" />
                      Run Structured Multi-Paper Comparison
                    </button>
                  </div>
                ) : null}
              </div>

              <div className={hasMessages ? "pt-2" : "pt-8 sm:pt-10"}>
                {messages.map((message) => (
                  <MessageBubble key={message.id} message={message} />
                ))}
              </div>
              <div ref={bottomRef} />
            </div>
          </section>

          <InputBar
            value={input}
            onValueChange={setInput}
            onSend={() => sendMessage(input)}
            onUpload={handleUpload}
            isSending={isSending}
            isUploading={isUploading}
            uploadLabel={uploadLabel}
            hasMessages={hasMessages}
          />
        </div>
      </main>
    </div>
  );
}
