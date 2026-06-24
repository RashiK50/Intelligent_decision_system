import React from 'react';
import { Plus, MessageSquare, Trash2, History, PanelLeftClose, Settings } from 'lucide-react';

export default function Sidebar({
  threads,
  activeThreadId,
  onSelectThread,
  onNewChat,
  onDeleteThread,
  onClearHistory,
  isOpen,
  onToggle
}) {
  return (
    <aside
      className={`fixed inset-y-0 left-0 z-30 w-72 transform transition-transform duration-300 ease-in-out lg:static lg:translate-x-0 glass-panel flex flex-col ${
        isOpen ? 'translate-x-0' : '-translate-x-full'
      }`}
    >
      {/* Header */}
      <div className="h-16 px-6 border-b border-slate-800/60 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <span className="font-display font-extrabold text-white text-base">E</span>
          </div>
          <div>
            <h1 className="font-display font-bold text-sm tracking-tight text-white leading-none">Decision Intel</h1>
            <span className="text-[14px] text-indigo-400/80 font-medium tracking-widest uppercase">Platform</span>
          </div>
        </div>
        <button 
          onClick={onToggle} 
          className="lg:hidden p-1.5 rounded-lg text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
          title="Close sidebar"
        >
          <PanelLeftClose className="w-5 h-5" />
        </button>
      </div>

      {/* Action Button: New Chat */}
      <div className="p-4">
        <button
          onClick={onNewChat}
          id="btn-new-chat"
          className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl font-medium text-sm transition-all duration-200 shadow-md shadow-indigo-600/10 hover:shadow-indigo-500/20 active:scale-[0.98] group"
        >
          <Plus className="w-4 h-4 transition-transform group-hover:rotate-90" />
          <span>New Chat</span>
        </button>
      </div>

      {/* Threads History List */}
      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-1">
        <div className="flex items-center gap-2 px-3 py-1.5 text-xs font-semibold text-slate-500 uppercase tracking-wider">
          <History className="w-3.5 h-3.5" />
          <span>Recent Queries</span>
        </div>

        {threads.length === 0 ? (
          <div className="px-3 py-6 text-center">
            <p className="text-xs text-slate-500 italic">No chat history yet</p>
          </div>
        ) : (
          threads.map((thread) => {
            const isActive = thread.id === activeThreadId;
            return (
              <div
                key={thread.id}
                className={`group flex items-center justify-between rounded-xl transition-all duration-150 relative ${
                  isActive
                    ? 'bg-indigo-600/10 text-indigo-200 border border-indigo-500/20'
                    : 'text-slate-400 hover:bg-slate-800/40 hover:text-slate-200 border border-transparent'
                }`}
              >
                <button
                  onClick={() => onSelectThread(thread.id)}
                  className="flex-1 flex items-center gap-3 px-3 py-3 text-left text-xs font-medium truncate"
                  title={thread.title}
                >
                  <MessageSquare className={`w-4 h-4 flex-shrink-0 ${isActive ? 'text-indigo-400' : 'text-slate-500 group-hover:text-slate-400'}`} />
                  <span className="truncate">{thread.title}</span>
                </button>

                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteThread(thread.id);
                  }}
                  className="opacity-0 group-hover:opacity-100 p-2 mr-1 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-all duration-150"
                  title="Delete chat thread"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            );
          })
        )}
      </div>

      {/* Footer Area */}
      <div className="p-4 border-t border-slate-800/60 bg-slate-950/20 space-y-2">
        {threads.length > 0 && (
          <button
            onClick={onClearHistory}
            className="w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-xl border border-slate-800 hover:border-rose-900/30 hover:bg-rose-500/5 text-slate-400 hover:text-rose-400 text-xs font-medium transition-all duration-150"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Clear History</span>
          </button>
        )}
        <div className="flex items-center justify-between px-2 pt-1 text-[15px] text-slate-500">
          <span className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
            Agent cluster active
          </span>
          <span className="font-mono text-[13px] bg-slate-900 px-1.5 py-0.5 rounded border border-slate-800">v1.0.0</span>
        </div>
      </div>
    </aside>
  );
}
