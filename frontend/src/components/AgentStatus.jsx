import React, { useState, useEffect } from 'react';
import { ShieldCheck, Target, Layers, FileCode, CheckCircle, Database, Award, Loader2 } from 'lucide-react';

const AGENT_STEPS = [
  { id: 'guardrail', name: 'Guardrail Agent', desc: 'Validating safety and business domain alignment', icon: ShieldCheck },
  { id: 'intent', name: 'Intent Classifier', desc: 'Determining analytics intent and entity metrics', icon: Target },
  { id: 'planner', name: 'Schema Planner', desc: 'Analyzing tables & constructing optimal SQL JOIN paths', icon: Layers },
  { id: 'sql_gen', name: 'SQL Generator', desc: 'Writing dialect-compliant SQL query structure', icon: FileCode },
  { id: 'sql_val', name: 'SQL Validator', desc: 'Verifying syntax, schema rules & access permissions', icon: CheckCircle },
  { id: 'db_exec', name: 'Database Executor', desc: 'Querying live Supabase database engine securely', icon: Database },
  { id: 'synthesizer', name: 'Insight Synthesizer', desc: 'Aggregating raw results and compiling business insights', icon: Award },
];

export default function AgentStatus() {
  const [currentStepIndex, setCurrentStepIndex] = useState(0);

  // Simulate progress step transitions to keep the interface highly engaging
  useEffect(() => {
    // Transition steps: faster at first, slower toward execution
    const intervals = [1200, 1500, 2000, 2000, 1500, 2000, 99999]; // last step waits indefinitely until resolution
    
    let timer;
    const runNextStep = (index) => {
      if (index < AGENT_STEPS.length - 1) {
        timer = setTimeout(() => {
          setCurrentStepIndex(index + 1);
          runNextStep(index + 1);
        }, intervals[index]);
      }
    };

    runNextStep(0);

    return () => {
      if (timer) clearTimeout(timer);
    };
  }, []);

  return (
    <div className="w-full max-w-2xl mx-auto py-6 px-4">
      <div className="glass-card rounded-2xl p-6 border border-indigo-500/10 glow-border relative overflow-hidden bg-slate-950/40">
        
        {/* Animated glowing top border */}
        <div className="absolute top-0 left-0 right-0 h-[1.5px] bg-gradient-to-r from-transparent via-indigo-500 to-transparent animate-[pulse_2s_infinite]"></div>

        <div className="flex items-start gap-4">
          {/* Pulsing Core Loader */}
          <div className="relative flex-shrink-0 flex items-center justify-center w-12 h-12 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
            <Loader2 className="w-6 h-6 animate-spin text-indigo-500" />
            <span className="absolute -top-1 -right-1 flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-indigo-500"></span>
            </span>
          </div>

          {/* Core Info */}
          <div className="flex-1 min-w-0">
            <h3 className="font-display font-semibold text-sm text-white tracking-tight flex items-center gap-2">
              Multi-Agent Analysis in Progress...
            </h3>
            <p className="text-xs text-indigo-400/80 mt-0.5">
              Active node: <span className="font-semibold">{AGENT_STEPS[currentStepIndex].name}</span>
            </p>
            <p className="text-xs text-slate-400 mt-1 italic">
              &ldquo;{AGENT_STEPS[currentStepIndex].desc}&rdquo;
            </p>
          </div>
        </div>

        {/* Step Progress Visualizer */}
        <div className="mt-6 space-y-3 border-t border-slate-900/60 pt-4">
          <div className="flex items-center justify-between text-[14px] text-slate-500 font-semibold tracking-wider uppercase mb-1">
            <span>Agent Workflow Map</span>
            <span>{Math.round((currentStepIndex / (AGENT_STEPS.length - 1)) * 100)}% Complete</span>
          </div>

          {/* Compact Mini Steps */}
          <div className="grid grid-cols-7 gap-1.5 h-1.5 w-full bg-slate-900 rounded-full overflow-hidden">
            {AGENT_STEPS.map((step, idx) => {
              const isPast = idx < currentStepIndex;
              const isActive = idx === currentStepIndex;
              return (
                <div
                  key={step.id}
                  className={`h-full rounded-full transition-all duration-300 ${
                    isPast
                      ? 'bg-gradient-to-r from-indigo-600 to-indigo-500'
                      : isActive
                      ? 'bg-indigo-400 animate-pulse'
                      : 'bg-slate-800'
                  }`}
                />
              );
            })}
          </div>

          {/* Micro layout details */}
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 mt-4 text-[15px]">
            {AGENT_STEPS.map((step, idx) => {
              const isPast = idx < currentStepIndex;
              const isActive = idx === currentStepIndex;
              const StepIcon = step.icon;
              return (
                <div
                  key={step.id}
                  className={`flex items-center gap-1 transition-all duration-200 ${
                    isPast
                      ? 'text-indigo-400'
                      : isActive
                      ? 'text-white font-medium scale-[1.02]'
                      : 'text-slate-600'
                  }`}
                >
                  <StepIcon className={`w-3.5 h-3.5 ${isActive ? 'animate-pulse text-indigo-400' : ''}`} />
                  <span className="hidden sm:inline text-[13px] font-semibold">{step.name.split(' ')[0]}</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
