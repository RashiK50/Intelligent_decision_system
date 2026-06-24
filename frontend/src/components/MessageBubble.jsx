import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Copy, Check, Terminal, AlertTriangle, RefreshCw, Bot, User } from 'lucide-react';

// CodeBlock Helper Component with Clipboard Copying
function CodeBlock({ value, language }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy text: ', err);
    }
  };

  return (
    <div className="my-4 rounded-xl border border-slate-800/80 bg-slate-950 overflow-hidden shadow-lg">
      <div className="flex items-center justify-between px-4 py-2 border-b border-slate-900 bg-slate-900/60">
        <div className="flex items-center gap-1.5 text-slate-400 font-mono text-[14px] uppercase font-semibold">
          <Terminal className="w-3.5 h-3.5 text-indigo-400" />
          <span>{language || 'code'}</span>
        </div>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 text-[14px] font-medium px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors"
          title="Copy code"
        >
          {copied ? (
            <>
              <Check className="w-3 h-3 text-emerald-400" />
              <span className="text-emerald-400">Copied</span>
            </>
          ) : (
            <>
              <Copy className="w-3 h-3" />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>
      <div className="p-4 overflow-x-auto">
        <pre className="m-0 p-0 bg-transparent border-none">
          <code className="text-xs text-slate-300 font-mono leading-relaxed block">{value}</code>
        </pre>
      </div>
    </div>
  );
}

export default function MessageBubble({ message, onRetry }) {
  const isUser = message.role === 'user';
  const isError = message.isError;

  return (
    <div
      className={`flex w-full gap-4 py-6 border-b border-slate-900/40 px-4 sm:px-6 md:px-8 transition-all animate-[fadeIn_0.2s_ease-out] ${
        isUser ? 'bg-slate-950/20' : 'bg-slate-900/10'
      }`}
    >
      <div className="max-w-4xl mx-auto w-full flex items-start gap-4">
        {/* Avatar */}
        <div
          className={`w-9 h-9 rounded-xl flex-shrink-0 flex items-center justify-center border shadow-sm ${
            isUser
              ? 'bg-slate-800/80 border-slate-700 text-slate-300'
              : isError
              ? 'bg-rose-500/10 border-rose-500/20 text-rose-400'
              : 'bg-gradient-to-tr from-indigo-600 to-violet-500 border-indigo-500/20 text-white'
          }`}
        >
          {isUser ? <User className="w-4.5 h-4.5" /> : <Bot className="w-4.5 h-4.5" />}
        </div>

        {/* Content Box */}
        <div className="flex-1 min-w-0">
          {/* Sender & Timestamp */}
          <div className="flex items-center gap-2 mb-1.5">
            <span className="text-xs font-semibold text-white tracking-wide font-display">
              {isUser ? 'You' : 'Decision Intel Core'}
            </span>
            <span className="text-[14px] text-slate-500 font-mono">
              {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
          </div>

          {/* Message Content */}
          {isUser ? (
            <p className="text-lg text-slate-200 leading-relaxed font-medium whitespace-pre-wrap">
              {message.content}
            </p>
          ) : isError ? (
            <div className="rounded-xl border border-rose-500/20 bg-rose-500/5 p-4 flex gap-3">
              <AlertTriangle className="w-5 h-5 text-rose-400 flex-shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                <p className="text-sm text-rose-200 font-medium leading-relaxed">
                  {message.content}
                </p>
                {onRetry && (
                  <button
                    onClick={onRetry}
                    className="mt-3 flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 hover:text-white text-xs font-semibold transition-all border border-rose-500/10 active:scale-95 cursor-pointer"
                  >
                    <RefreshCw className="w-3.5 h-3.5" />
                    <span>Retry Request</span>
                  </button>
                )}
              </div>
            </div>
          ) : (
            <div className="prose-custom">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  // Render links with standard absolute file target formats if local or standard browser behavior
                  a: ({ node, href, children, ...props }) => (
                    <a
                      href={href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-indigo-400 hover:text-indigo-300 underline font-medium transition-colors"
                      {...props}
                    >
                      {children}
                    </a>
                  ),
                  // Wrap table elements in responsive scroll containers
                  table: ({ node, ...props }) => (
                    <div className="overflow-x-auto max-w-full w-full rounded-xl border border-slate-800/80 bg-slate-950/20 my-5">
                      <table className="min-w-full border-collapse" {...props} />
                    </div>
                  ),
                  // Render standard pre blocks as CodeBlock to support copying
                  code: ({ node, inline, className, children, ...props }) => {
                    const match = /language-(\w+)/.exec(className || '');
                    const codeVal = String(children).replace(/\n$/, '');
                    return !inline && match ? (
                      <CodeBlock value={codeVal} language={match[1]} />
                    ) : inline ? (
                      <code className="bg-slate-900 text-indigo-300 px-1.5 py-0.5 rounded text-xs border border-slate-800/80 font-mono font-normal" {...props}>
                        {children}
                      </code>
                    ) : (
                      <CodeBlock value={codeVal} language="sql" />
                    );
                  }
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
