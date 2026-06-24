import React, { useState, useEffect, useRef } from 'react';
import ChatLayout from './components/ChatLayout';
import Sidebar from './components/Sidebar';
import MessageBubble from './components/MessageBubble';
import ChatInput from './components/ChatInput';
import AgentStatus from './components/AgentStatus';
import { Database, HelpCircle, BarChart3, LineChart, Sparkles, MessageSquare } from 'lucide-react';

const SUGGESTIONS = [
  {
    title: 'Sales Performance',
    prompt: 'What are the top 5 selling products by revenue, and how much did they generate?',
    icon: BarChart3,
    color: 'text-indigo-400 border-indigo-500/20 bg-indigo-500/5'
  },
  {
    title: 'Inventory Status',
    prompt: 'Analyze current product stock levels and identify items with critical shortage (under 20 units).',
    icon: Database,
    color: 'text-violet-400 border-violet-500/20 bg-violet-500/5'
  },
  {
    title: 'Customer Retention',
    prompt: 'Compare customer registration trends and retention rates over the last 3 quarters.',
    icon: LineChart,
    color: 'text-cyan-400 border-cyan-500/20 bg-cyan-500/5'
  }
];

// Utility to generate unique session thread IDs
const generateUUID = () => {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
};

export default function App() {
  const [threads, setThreads] = useState([]);
  const [activeThreadId, setActiveThreadId] = useState(null);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  
  const messagesEndRef = useRef(null);

  // 1. Initial Load: Read from LocalStorage or seed a new thread
  useEffect(() => {
    const savedThreads = localStorage.getItem('di_platform_threads');
    const savedActiveId = localStorage.getItem('di_platform_active_thread_id');
    
    if (savedThreads) {
      const parsedThreads = JSON.parse(savedThreads);
      setThreads(parsedThreads);
      if (savedActiveId && parsedThreads.some(t => t.id === savedActiveId)) {
        setActiveThreadId(savedActiveId);
      } else if (parsedThreads.length > 0) {
        setActiveThreadId(parsedThreads[0].id);
      }
    } else {
      // Seed first thread
      handleNewChat();
    }
  }, []);

  // 2. Persist state changes to LocalStorage
  useEffect(() => {
    if (threads.length > 0) {
      localStorage.setItem('di_platform_threads', JSON.stringify(threads));
    } else {
      localStorage.removeItem('di_platform_threads');
    }
  }, [threads]);

  useEffect(() => {
    if (activeThreadId) {
      localStorage.setItem('di_platform_active_thread_id', activeThreadId);
    } else {
      localStorage.removeItem('di_platform_active_thread_id');
    }
  }, [activeThreadId]);

  // 3. Auto-scroll to the bottom of message list
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [threads, isLoading]);

  // 4. New Chat Creation Handler
  const handleNewChat = () => {
    const newId = generateUUID();
    const newThread = {
      id: newId,
      title: 'New Analytics Session',
      messages: [],
      timestamp: new Date().toISOString()
    };
    
    setThreads(prev => [newThread, ...prev]);
    setActiveThreadId(newId);
    setInput('');
    setIsLoading(false);
  };

  // 5. Select Thread Handler
  const handleSelectThread = (id) => {
    setActiveThreadId(id);
    setInput('');
    setIsLoading(false);
  };

  // 6. Delete Individual Thread Handler
  const handleDeleteThread = (id) => {
    const updated = threads.filter(t => t.id !== id);
    setThreads(updated);
    
    if (activeThreadId === id) {
      if (updated.length > 0) {
        setActiveThreadId(updated[0].id);
      } else {
        // Automatically create a new thread if history is empty
        const newId = generateUUID();
        const freshThread = {
          id: newId,
          title: 'New Analytics Session',
          messages: [],
          timestamp: new Date().toISOString()
        };
        setThreads([freshThread]);
        setActiveThreadId(newId);
      }
    }
  };

  // 7. Clear All History Handler
  const handleClearHistory = () => {
    setThreads([]);
    setActiveThreadId(null);
    localStorage.removeItem('di_platform_threads');
    localStorage.removeItem('di_platform_active_thread_id');
    
    // Instantiate a fresh startup session
    const newId = generateUUID();
    const freshThread = {
      id: newId,
      title: 'New Analytics Session',
      messages: [],
      timestamp: new Date().toISOString()
    };
    setThreads([freshThread]);
    setActiveThreadId(newId);
  };

  // 8. Submit Chat Message to FastAPI
  const handleSendMessage = async (customPrompt = null) => {
    const queryText = customPrompt || input;
    if (!queryText.trim() || isLoading) return;

    setInput('');
    setIsLoading(true);

    const userMessage = {
      id: generateUUID(),
      role: 'user',
      content: queryText,
      timestamp: new Date().toISOString()
    };

    // Update active thread with User message and set title if default
    setThreads(prevThreads => {
      return prevThreads.map(thread => {
        if (thread.id === activeThreadId) {
          const updatedMessages = [...thread.messages, userMessage];
          const hasDefaultTitle = thread.title === 'New Analytics Session' || thread.messages.length === 0;
          return {
            ...thread,
            title: hasDefaultTitle ? (queryText.length > 40 ? `${queryText.substring(0, 40)}...` : queryText) : thread.title,
            messages: updatedMessages
          };
        }
        return thread;
      });
    });

    try {
      // Connect to root backend api running on local port (utilizing local dev server proxy '/api')
      const response = await fetch('/api/v1/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_query: queryText,
          thread_id: activeThreadId
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP Error Status: ${response.status}`);
      }

      const data = await response.json();

      const aiMessage = {
        id: generateUUID(),
        role: 'assistant',
        content: data.formatted_response,
        timestamp: new Date().toISOString()
      };

      setThreads(prevThreads => {
        return prevThreads.map(thread => {
          if (thread.id === activeThreadId) {
            return {
              ...thread,
              messages: [...thread.messages, aiMessage]
            };
          }
          return thread;
        });
      });

    } catch (err) {
      console.error('API call failure:', err);
      
      const errorMessage = {
        id: generateUUID(),
        role: 'assistant',
        content: 'The platform encountered an error processing your request. Please try modifying your question or starting a new chat.',
        timestamp: new Date().toISOString(),
        isError: true
      };

      setThreads(prevThreads => {
        return prevThreads.map(thread => {
          if (thread.id === activeThreadId) {
            return {
              ...thread,
              messages: [...thread.messages, errorMessage]
            };
          }
          return thread;
        });
      });
    } finally {
      setIsLoading(false);
    }
  };

  const activeThread = threads.find(t => t.id === activeThreadId) || { messages: [], title: '' };

  return (
    <ChatLayout
      sidebarOpen={sidebarOpen}
      onToggleSidebar={() => setSidebarOpen(prev => !prev)}
      activeThreadTitle={activeThread.title}
    >
      {/* Sidebar Child (slot 0) */}
      <Sidebar
        threads={threads}
        activeThreadId={activeThreadId}
        onSelectThread={handleSelectThread}
        onNewChat={handleNewChat}
        onDeleteThread={handleDeleteThread}
        onClearHistory={handleClearHistory}
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(false)}
      />

      {/* Conversation Area (slot 1) */}
      <main className="flex-1 flex flex-col justify-between overflow-hidden bg-[#0c101d]">
        
        {/* Messages Scroll Panel */}
        <div className="flex-1 overflow-y-auto overflow-x-hidden">
          {activeThread.messages.length === 0 ? (
            /* Welcome / Initial Dashboard Screen */
            <div className="max-w-3xl mx-auto px-6 py-12 md:py-20 flex flex-col justify-center items-center min-h-[70vh]">
              <div className="w-16 h-16 rounded-2xl bg-indigo-600/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center mb-6 shadow-xl shadow-indigo-500/5 animate-pulse">
                <Sparkles className="w-8 h-8" />
              </div>
              <h1 className="font-display font-extrabold text-3xl md:text-4xl text-center tracking-tight text-white mb-2 leading-none">
                Decision Intelligence Platform
              </h1>
              <p className="text-sm md:text-base text-slate-400 text-center max-w-xl mb-12">
                Ask business questions in plain English. The platform compiles schemas, drafts secure SQL, queries Postgres, and returns insights.
              </p>

              {/* Suggestions Cards */}
              <div className="w-full space-y-4">
                <h4 className="text-[15px] font-semibold text-slate-500 uppercase tracking-widest text-center mb-1">
                  Start with a template query
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 w-full">
                  {SUGGESTIONS.map((sug, idx) => {
                    const SugIcon = sug.icon;
                    return (
                      <button
                        key={idx}
                        onClick={() => handleSendMessage(sug.prompt)}
                        className={`p-4 text-left rounded-2xl border transition-all duration-200 cursor-pointer text-slate-300 hover:text-white glass-card-hover flex flex-col justify-between h-36 ${sug.color}`}
                      >
                        <div className="flex items-center justify-between w-full">
                          <SugIcon className="w-5 h-5" />
                          <MessageSquare className="w-3.5 h-3.5 opacity-40 group-hover:opacity-100" />
                        </div>
                        <div className="mt-4">
                          <h5 className="font-semibold text-xs text-white">{sug.title}</h5>
                          <p className="text-[15px] text-slate-400 line-clamp-2 mt-1 leading-normal">
                            {sug.prompt}
                          </p>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          ) : (
            /* Render active conversation messages */
            <div className="flex flex-col w-full pb-8">
              {activeThread.messages.map((message) => (
                <MessageBubble
                  key={message.id}
                  message={message}
                  onRetry={() => handleSendMessage(message.content)}
                />
              ))}

              {/* Display agent execution status indicator */}
              {isLoading && <AgentStatus />}
              
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input Bar area */}
        <div className="p-4 border-t border-slate-900 bg-slate-950/20 flex-shrink-0">
          <ChatInput
            input={input}
            setInput={setInput}
            onSubmit={() => handleSendMessage()}
            isLoading={isLoading}
          />
        </div>
      </main>
    </ChatLayout>
  );
}
