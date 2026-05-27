"use client";

import { Bot, FileText, PanelLeftClose, PanelLeftOpen, SlidersHorizontal, X } from "lucide-react";
import { DocumentMetadata, ModelProvider } from "@/lib/api";
import { cn } from "@/lib/utils";

export type QueryMode = "current" | "selected" | "all";

interface SidebarProps {
  provider: ModelProvider;
  model: string;
  models: string[];
  chunkSize: number;
  topK: number;
  denseWeight: number;
  bm25Weight: number;
  candidatePoolSize: number;
  documents: DocumentMetadata[];
  selectedDocumentIds: string[];
  queryMode: QueryMode;
  isOpen: boolean;
  isCollapsed: boolean;
  onClose: () => void;
  onToggleCollapse: () => void;
  onProviderChange: (value: ModelProvider) => void;
  onModelChange: (value: string) => void;
  onChunkSizeChange: (value: number) => void;
  onTopKChange: (value: number) => void;
  onDenseWeightChange: (value: number) => void;
  onBm25WeightChange: (value: number) => void;
  onCandidatePoolSizeChange: (value: number) => void;
  onDocumentSelectionChange: (documentIds: string[]) => void;
  onQueryModeChange: (value: QueryMode) => void;
}

export function Sidebar({
  provider,
  model,
  models,
  chunkSize,
  topK,
  denseWeight,
  bm25Weight,
  candidatePoolSize,
  documents,
  selectedDocumentIds,
  queryMode,
  isOpen,
  isCollapsed,
  onClose,
  onToggleCollapse,
  onProviderChange,
  onModelChange,
  onChunkSizeChange,
  onTopKChange,
  onDenseWeightChange,
  onBm25WeightChange,
  onCandidatePoolSizeChange,
  onDocumentSelectionChange,
  onQueryModeChange
}: SidebarProps) {
  const selectedDocuments = new Set(selectedDocumentIds);
  const toggleDocument = (documentId: string) => {
    const next = selectedDocuments.has(documentId)
      ? selectedDocumentIds.filter((item) => item !== documentId)
      : [...selectedDocumentIds, documentId];
    onDocumentSelectionChange(next);
  };

  return (
    <>
      <div
        className={cn(
          "fixed inset-0 z-30 bg-black/55 backdrop-blur-sm transition lg:hidden",
          isOpen ? "pointer-events-auto opacity-100" : "pointer-events-none opacity-0"
        )}
        onClick={onClose}
      />

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex shrink-0 flex-col border-r border-emerald-500/10 bg-black/60 backdrop-blur-2xl backdrop-saturate-150 transition-all duration-300 lg:static lg:z-0",
          isOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0",
          isCollapsed ? "w-[78px]" : "w-[280px]"
        )}
        style={{ boxShadow: 'inset -1px 0 0 0 rgba(16,185,129,0.07)' }}
      >
        <div className={cn("flex items-center px-4 py-4", isCollapsed ? "justify-center" : "justify-between")}>
          {!isCollapsed ? (
            <div>
              <div className="text-[10px] uppercase tracking-[0.3em] text-slate-500">
                Controls
              </div>
              <h2 className="mt-2 text-xl font-semibold text-white">Settings</h2>
            </div>
          ) : null}

          <div className="flex items-center gap-2">
            <button
              type="button"
              className="hidden h-10 w-10 items-center justify-center rounded-2xl border border-white/10 bg-white/5 text-slate-300 transition hover:bg-white/10 lg:inline-flex"
              onClick={onToggleCollapse}
              aria-label={isCollapsed ? "Expand controls" : "Collapse controls"}
            >
              {isCollapsed ? <PanelLeftOpen className="h-5 w-5" /> : <PanelLeftClose className="h-5 w-5" />}
            </button>

            <button
              type="button"
              className="inline-flex h-10 w-10 items-center justify-center rounded-2xl border border-white/10 bg-white/5 text-slate-300 transition hover:bg-white/10 lg:hidden"
              onClick={onClose}
              aria-label="Close controls"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {isCollapsed ? (
          <div className="flex flex-1 flex-col items-center gap-4 px-3 pt-6">
            <button
              type="button"
              className="inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-accent/20 bg-accent/10 text-accent"
              onClick={onToggleCollapse}
              aria-label="Expand settings"
            >
              <SlidersHorizontal className="h-5 w-5" />
            </button>
            <div className="text-center text-[11px] leading-5 text-slate-500 [writing-mode:vertical-rl] [text-orientation:mixed]">
              research controls
            </div>
          </div>
        ) : (
          <div className="scrollbar-thin flex-1 overflow-y-auto px-4 pb-5">
            <p className="mb-5 text-sm leading-6 text-slate-400">
              Keep the focus on the conversation. OpenRouter is the default provider, and you can switch models any time.
            </p>

            <div className="space-y-4">
              {documents.length > 0 ? (
                <div className="rounded-3xl border border-white/10 bg-white/[0.04] p-4">
                  <label className="mb-3 flex items-center gap-2 text-sm font-medium text-slate-200">
                    <FileText className="h-4 w-4 text-accent" />
                    Documents
                  </label>
                  <div className="space-y-2">
                    <div className="grid grid-cols-3 gap-1 rounded-2xl border border-white/8 bg-black/20 p-1 text-xs">
                      {([
                        ["current", "Current"],
                        ["selected", "Selected"],
                        ["all", "All"]
                      ] as const).map(([value, label]) => (
                        <button
                          key={value}
                          type="button"
                          className={cn(
                            "rounded-xl px-2 py-2 text-slate-300 transition hover:bg-white/8",
                            queryMode === value && "bg-accent/15 text-accent"
                          )}
                          onClick={() => onQueryModeChange(value)}
                        >
                          {label}
                        </button>
                      ))}
                    </div>

                    {documents.map((document) => (
                      <label
                        key={document.document_id}
                        className="flex cursor-pointer items-start gap-3 rounded-2xl border border-white/8 bg-black/15 p-3 text-sm text-slate-200 transition hover:bg-white/[0.05]"
                      >
                        <input
                          type="checkbox"
                          className="mt-1 accent-[#9AE6B4]"
                          checked={selectedDocuments.has(document.document_id)}
                          onChange={() => toggleDocument(document.document_id)}
                        />
                        <span className="min-w-0">
                          <span className="block truncate">{document.filename}</span>
                          <span className="mt-1 block text-xs text-slate-500">
                            {document.chunk_count} chunks
                            {document.extraction?.total_pages ? ` | ${document.extraction.total_pages} pages` : ""}
                            {document.extraction?.empty_pages?.length ? ` | ${document.extraction.empty_pages.length} empty` : ""}
                          </span>
                        </span>
                      </label>
                    ))}
                  </div>
                </div>
              ) : null}

              <div className="rounded-3xl border border-white/10 bg-white/[0.04] p-4">
                <label className="mb-3 flex items-center gap-2 text-sm font-medium text-slate-200">
                  <Bot className="h-4 w-4 text-accent" />
                  Provider
                </label>
                <select
                  value={provider}
                  className="w-full rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-white outline-none transition focus:border-accent/40"
                  onChange={(event) => onProviderChange(event.target.value as ModelProvider)}
                >
                  <option value="openrouter">OpenRouter</option>
                  <option value="ollama">Ollama</option>
                </select>
              </div>

              <div className="rounded-3xl border border-white/10 bg-white/[0.04] p-4">
                <label className="mb-3 flex items-center gap-2 text-sm font-medium text-slate-200">
                  <SlidersHorizontal className="h-4 w-4 text-accent" />
                  Model
                </label>
                <select
                  value={model}
                  className="w-full rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-white outline-none transition focus:border-accent/40"
                  onChange={(event) => onModelChange(event.target.value)}
                >
                  {models.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </div>

              <div className="rounded-3xl border border-white/10 bg-white/[0.04] p-4">
                <div className="flex items-center justify-between text-sm text-slate-200">
                  <span>Chunk size</span>
                  <span className="font-[family-name:var(--font-mono)] text-accent">{chunkSize}</span>
                </div>
                <input
                  type="range"
                  min={300}
                  max={1200}
                  step={50}
                  value={chunkSize}
                  className="mt-4 w-full accent-[#9AE6B4]"
                  onChange={(event) => onChunkSizeChange(Number(event.target.value))}
                />
              </div>

              <div className="rounded-3xl border border-white/10 bg-white/[0.04] p-4">
                <div className="flex items-center justify-between text-sm text-slate-200">
                  <span>Top-k retrieval</span>
                  <span className="font-[family-name:var(--font-mono)] text-accent">{topK}</span>
                </div>
                <input
                  type="range"
                  min={2}
                  max={8}
                  step={1}
                  value={topK}
                  className="mt-4 w-full accent-[#9AE6B4]"
                  onChange={(event) => onTopKChange(Number(event.target.value))}
                />
              </div>

              <div className="rounded-3xl border border-white/10 bg-white/[0.04] p-4">
                <label className="mb-3 flex items-center gap-2 text-sm font-medium text-slate-200">
                  <SlidersHorizontal className="h-4 w-4 text-accent" />
                  Hybrid retrieval
                </label>

                <div className="space-y-4">
                  <div>
                    <div className="flex items-center justify-between text-sm text-slate-200">
                      <span>Dense weight</span>
                      <span className="font-[family-name:var(--font-mono)] text-accent">{denseWeight.toFixed(2)}</span>
                    </div>
                    <input
                      type="range"
                      min={0}
                      max={1}
                      step={0.05}
                      value={denseWeight}
                      className="mt-3 w-full accent-[#9AE6B4]"
                      onChange={(event) => onDenseWeightChange(Number(event.target.value))}
                    />
                  </div>

                  <div>
                    <div className="flex items-center justify-between text-sm text-slate-200">
                      <span>BM25 weight</span>
                      <span className="font-[family-name:var(--font-mono)] text-accent">{bm25Weight.toFixed(2)}</span>
                    </div>
                    <input
                      type="range"
                      min={0}
                      max={1}
                      step={0.05}
                      value={bm25Weight}
                      className="mt-3 w-full accent-[#9AE6B4]"
                      onChange={(event) => onBm25WeightChange(Number(event.target.value))}
                    />
                  </div>

                  <div>
                    <div className="flex items-center justify-between text-sm text-slate-200">
                      <span>Candidate pool</span>
                      <span className="font-[family-name:var(--font-mono)] text-accent">{candidatePoolSize}</span>
                    </div>
                    <input
                      type="range"
                      min={8}
                      max={60}
                      step={4}
                      value={candidatePoolSize}
                      className="mt-3 w-full accent-[#9AE6B4]"
                      onChange={(event) => onCandidatePoolSizeChange(Number(event.target.value))}
                    />
                  </div>

                  <label className="flex items-center justify-between gap-3 text-sm text-slate-400">
                    <span>Reranker</span>
                    <input type="checkbox" disabled className="accent-[#9AE6B4] opacity-50" />
                  </label>
                </div>
              </div>
            </div>
          </div>
        )}
      </aside>
    </>
  );
}
