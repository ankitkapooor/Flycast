import React from "react";
import Link from "next/link";
import { ArrowRight, ArrowDown } from "lucide-react";
import { ScientificCaveat } from "./ScientificCaveat";

export const Hero: React.FC = () => {
  return (
    <section className="relative pt-8 pb-14 border-b border-paper-border">
      <div className="mx-auto max-w-4xl px-4 sm:px-6 text-center space-y-8">
        {/* Editorial Subtitle */}
        <div className="inline-flex items-center gap-2 border border-paper-border bg-paper-dark/70 px-3 py-1 rounded text-[11px] font-mono uppercase tracking-widest text-foreground/70">
          <span>FLYCAST / EXPERIMENT 001</span>
          <span className="text-paper-border">|</span>
          <span>COMPUTATIONAL CONNECTOMICS</span>
        </div>

        {/* Main Headline */}
        <div className="space-y-4">
          <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-foreground font-sans max-w-2xl mx-auto leading-tight">
            Can a fruit fly <br className="hidden sm:inline" />
            <span className="italic font-serif font-normal text-fly">predict the future?</span>
          </h1>
          <p className="text-base sm:text-lg text-foreground/70 max-w-xl mx-auto font-sans leading-relaxed">
            Run your time series through the wiring diagram of a real biological nervous system.
            166,691 biological neurons. One frozen connectome. Your data.
          </p>
        </div>

        {/* Action Button */}
        <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link
            href="/experiment"
            className="inline-flex items-center justify-center gap-3 bg-fly hover:bg-fly-hover text-white px-7 py-3.5 rounded-sm font-mono text-xs uppercase tracking-widest font-semibold shadow-sm transition-all hover:translate-y-[-1px]"
          >
            <span>Run An Experiment</span>
            <ArrowRight className="h-4 w-4" />
          </Link>
          <Link
            href="/method"
            className="inline-flex items-center justify-center gap-2 border border-paper-border hover:bg-paper-dark text-foreground/80 px-6 py-3.5 rounded-sm font-mono text-xs uppercase tracking-wider transition-colors"
          >
            <span>Read Methodology</span>
          </Link>
        </div>

        {/* Visual Sequence Diagram */}
        <div className="pt-8 max-w-xl mx-auto">
          <div className="grid grid-cols-1 sm:grid-cols-5 items-center gap-2 font-mono text-xs text-foreground/80 border border-paper-border bg-paper-light p-4 rounded-sm">
            <div className="p-2 bg-paper-dark/80 rounded border border-paper-border text-center">
              <span className="font-bold block text-foreground">YOUR SIGNAL</span>
              <span className="text-[10px] text-foreground/60">Time Series</span>
            </div>

            <div className="flex justify-center text-foreground/40 sm:rotate-[-90deg]">
              <ArrowDown className="h-4 w-4" />
            </div>

            <div className="p-2 bg-fly/10 rounded border border-fly/30 text-center">
              <span className="font-bold block text-fly">166K CNS NODES</span>
              <span className="text-[10px] text-fly/80">Recurrent Reservoir</span>
            </div>

            <div className="flex justify-center text-foreground/40 sm:rotate-[-90deg]">
              <ArrowDown className="h-4 w-4" />
            </div>

            <div className="p-2 bg-paper-dark/80 rounded border border-paper-border text-center">
              <span className="font-bold block text-foreground">FORECAST</span>
              <span className="text-[10px] text-foreground/60">Direct Readout</span>
            </div>
          </div>
        </div>

        <div className="max-w-2xl mx-auto pt-4 text-left">
          <ScientificCaveat />
        </div>
      </div>
    </section>
  );
};
