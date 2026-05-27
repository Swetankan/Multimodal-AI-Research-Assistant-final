"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { CodeBlock } from "./CodeBlock";

export function MarkdownRenderer({ content }: { content: string }) {
  return (
    <div className="text-[15px] leading-7 text-slate-100">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          p({ children }) {
            return <p className="my-4 first:mt-0 last:mb-0">{children}</p>;
          },
          strong({ children }) {
            return <strong className="font-semibold text-white">{children}</strong>;
          },
          em({ children }) {
            return <em className="italic text-slate-200">{children}</em>;
          },
          ul({ children }) {
            return <ul className="my-4 list-disc space-y-1 pl-6">{children}</ul>;
          },
          ol({ children }) {
            return <ol className="my-4 list-decimal space-y-1 pl-6">{children}</ol>;
          },
          li({ children }) {
            return <li className="pl-1">{children}</li>;
          },
          a({ href, children }) {
            return (
              <a
                href={href}
                target="_blank"
                rel="noreferrer"
                className="text-accent underline decoration-accent/30 underline-offset-4 transition hover:text-accentStrong"
              >
                {children}
              </a>
            );
          },
          blockquote({ children }) {
            return (
              <blockquote className="my-4 border-l-2 border-accent/40 pl-4 text-slate-300">
                {children}
              </blockquote>
            );
          },
          table({ children }) {
            return (
              <div className="my-6 overflow-x-auto rounded-xl border border-white/10 bg-white/[0.02] shadow-[0_4px_30px_rgba(0,0,0,0.1)] backdrop-blur">
                <table className="w-full border-collapse text-left text-sm text-slate-300">
                  {children}
                </table>
              </div>
            );
          },
          thead({ children }) {
            return <thead className="border-b border-white/10 bg-white/[0.04] text-xs font-semibold uppercase tracking-wider text-slate-200">{children}</thead>;
          },
          tbody({ children }) {
            return <tbody className="divide-y divide-white/5">{children}</tbody>;
          },
          tr({ children }) {
            return <tr className="hover:bg-white/[0.01] transition-colors">{children}</tr>;
          },
          th({ children }) {
            return <th className="px-4 py-3 font-semibold border-r border-white/5 last:border-r-0 text-white bg-white/[0.02]">{children}</th>;
          },
          td({ children }) {
            return <td className="px-4 py-3 leading-6 border-r border-white/5 last:border-r-0 align-top">{children}</td>;
          },
          code(props) {
            const { children, className } = props;
            const match = /language-(\w+)/.exec(className ?? "");
            const code = String(children).replace(/\n$/, "");

            if (match) {
              return <CodeBlock code={code} language={match[1]} />;
            }

            return (
              <code className="rounded-md bg-white/5 px-1.5 py-0.5 text-[0.9em] text-emerald-200">
                {children}
              </code>
            );
          }
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}