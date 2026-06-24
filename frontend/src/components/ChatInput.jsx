import React, { useRef, useEffect } from 'react';
import { Send, CornerDownLeft } from 'lucide-react';

export default function ChatInput({
  input,
  setInput,
  onSubmit,
  isLoading
}) {
  const textareaRef = useRef(null);

  // Auto-resize textarea height as text grows
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [input]);

  const handleKeyDown = (e) => {
    // Submit on Enter without Shift
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (input.trim() && !isLoading) {
        onSubmit();
      }
    }
  };

  const handleFormSubmit = (e) => {
    e.preventDefault();
    if (input.trim() && !isLoading) {
      onSubmit();
    }
  };

  return (
    <form onSubmit={handleFormSubmit} className="relative max-w-4xl mx-auto">
      <div className="relative flex items-end w-full bg-slate-900/80 hover:bg-slate-900 border border-slate-800/80 focus-within:border-indigo-500/50 rounded-2xl transition-all duration-200 shadow-xl shadow-black/10 focus-within:shadow-indigo-500/5 overflow-hidden">
        <textarea
          ref={textareaRef}
          rows={1}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
          id="chat-textarea"
          placeholder={isLoading ? "Please wait for agent analysis..." : "Ask a business intelligence question (e.g., 'What are the top-selling products in California?')..."}
          className="flex-1 max-h-[200px] py-4 pl-4 pr-16 bg-transparent text-sm text-slate-100 placeholder-slate-500 border-none outline-none resize-none focus:ring-0 leading-relaxed max-w-full"
        />

        <div className="absolute right-3 bottom-3 flex items-center gap-2">
          {input.trim() && !isLoading && (
            <span className="hidden md:flex items-center gap-0.5 text-[14px] text-slate-500 font-medium mr-1 select-none">
              <span>Send</span>
              <CornerDownLeft className="w-2.5 h-2.5" />
            </span>
          )}
          <button
            type="submit"
            id="btn-submit-message"
            disabled={!input.trim() || isLoading}
            className={`p-2.5 rounded-xl flex items-center justify-center transition-all duration-200 ${
              input.trim() && !isLoading
                ? 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/20 hover:shadow-indigo-500/30 active:scale-95 cursor-pointer'
                : 'bg-slate-800 text-slate-600 cursor-not-allowed'
            }`}
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
      <p className="text-[14px] text-center text-slate-500 mt-2 font-medium">
        Decision Intel utilizes advanced schema-aware LLMs to generate secure SQL statements against Supabase database.
      </p>
    </form>
  );
}
