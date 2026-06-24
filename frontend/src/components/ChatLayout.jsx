import React from 'react';
import { Menu, Info, HelpCircle } from 'lucide-react';

export default function ChatLayout({
  sidebarOpen,
  onToggleSidebar,
  activeThreadTitle,
  children
}) {
  return (
    <div className="flex h-screen w-screen bg-[#0b0f19] text-[#e2e8f0] overflow-hidden relative">
      
      {/* Sidebar overlay for mobile when open */}
      {sidebarOpen && (
        <div
          onClick={onToggleSidebar}
          className="fixed inset-0 z-20 bg-slate-950/80 backdrop-blur-sm lg:hidden transition-opacity duration-300"
        />
      )}

      {/* Actual sidebar is placed by App.jsx, layout manages overall window */}
      {children[0]}

      {/* Main Chat Window Panel */}
      <div className="flex-1 flex flex-col h-full overflow-hidden min-w-0">
        
        {/* Navigation / Header */}
        <header className="h-16 px-6 border-b border-slate-900 bg-slate-950/40 backdrop-blur-md flex items-center justify-between flex-shrink-0 z-10">
          <div className="flex items-center gap-3 min-w-0">
            <button
              onClick={onToggleSidebar}
              className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-900 border border-slate-800/40 lg:hidden transition-all"
              title="Toggle history panel"
            >
              <Menu className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-2 min-w-0">
              {/* Desktop Menu icon to toggle sidebar even on desktop */}
              <button
                onClick={onToggleSidebar}
                className="hidden lg:block p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-900 border border-slate-800/40 transition-all cursor-pointer"
                title="Toggle sidebar"
              >
                <Menu className="w-5 h-5" />
              </button>
              <div className="truncate">
                <h2 className="text-xs font-semibold text-white truncate font-display">
                  {activeThreadTitle || 'Enterprise Analysis System'}
                </h2>
                <div className="flex items-center gap-1 mt-0.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-pulse"></span>
                  <span className="text-[14px] text-slate-500 font-medium font-mono uppercase tracking-wider">Multi-Agent Mode</span>
                </div>
              </div>
            </div>
          </div>

          {/* Quick Header Actions */}
          <div className="flex items-center gap-3">
            <div className="hidden sm:flex items-center gap-1 text-[15px] font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 px-2.5 py-1 rounded-lg">
              <span>Database Engine: Supabase</span>
            </div>
            <a
              href="https://github.com"
              target="_blank"
              rel="noreferrer"
              className="p-2 text-slate-500 hover:text-slate-300 transition-colors"
              title="Help Documentation"
            >
              <HelpCircle className="w-5 h-5" />
            </a>
          </div>
        </header>

        {/* Conversation area and controls */}
        {children[1]}
        
      </div>
    </div>
  );
}
