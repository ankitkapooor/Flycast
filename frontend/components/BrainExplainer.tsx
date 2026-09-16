import React from "react";
import { GitBranch, BrainCircuit, LineChart, Cpu } from "lucide-react";

export const BrainExplainer: React.FC = () => {
  return (
    <section className="py-16 border-b border-paper-border">
      <div className="mx-auto max-w-4xl px-4 sm:px-6 space-y-10">
        <div className="space-y-2 text-center sm:text-left">
          <span className="font-mono text-xs uppercase tracking-widest text-fly font-semibold">
            01 / Concept & Thesis
          </span>
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
            What happens when you turn an insect nervous system into a computer?
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 text-sm leading-relaxed text-foreground/80 font-sans">
          <div className="space-y-4">
            <p>
              In 2026, researchers published the <strong>MaleCNS v1.0 connectome</strong> — a complete
              synapse-resolution electron-microscopy reconstruction of an entire male adult fruit-fly central nervous
              system, containing over 166,000 neurons and 25.5 million directed synaptic connections spanning the brain,
              optic lobes, and ventral nerve cord.
            </p>
            <p>
              <strong>FlyCast</strong> treats this biological wiring diagram as a fixed recurrent computational
              reservoir (an Echo State Network). Rather than training billions of artificial weights, the biological
              wiring remains completely frozen.
            </p>
          </div>

          <div className="space-y-4">
            <p>
              When your time-series values arrive, they stimulate 512 annotated sensory neurons. The signal ripples
              through the actual recurrent synaptic graph, creating rich nonlinear spatial-temporal trajectories.
            </p>
            <p>
              Only a lightweight linear Ridge readout is trained to map sampled internal network states to your future
              target values. If the fly predicts better than standard autoregression, the biological wiring provided
              genuine computational utility. If it fails, the application honestly tells you so.
            </p>
          </div>
        </div>

        {/* 4-Step Process Pipeline Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 pt-4 font-mono text-xs">
          <div className="p-4 border border-paper-border bg-paper-light space-y-2 rounded-sm">
            <div className="flex items-center gap-2 text-fly font-semibold">
              <span className="h-5 w-5 rounded-full bg-fly/10 flex items-center justify-center text-[10px]">1</span>
              <span>INPUT INJECTION</span>
            </div>
            <p className="text-foreground/70 leading-relaxed text-[11px]">
              Chronological data is standardized and deterministically mapped across 512 sensory CNS neurons.
            </p>
          </div>

          <div className="p-4 border border-paper-border bg-paper-light space-y-2 rounded-sm">
            <div className="flex items-center gap-2 text-fly font-semibold">
              <span className="h-5 w-5 rounded-full bg-fly/10 flex items-center justify-center text-[10px]">2</span>
              <span>FROZEN CNS</span>
            </div>
            <p className="text-foreground/70 leading-relaxed text-[11px]">
              Activity propagates through 25.58M real directed synaptic edges via leaky tanh rate dynamics.
            </p>
          </div>

          <div className="p-4 border border-paper-border bg-paper-light space-y-2 rounded-sm">
            <div className="flex items-center gap-2 text-fly font-semibold">
              <span className="h-5 w-5 rounded-full bg-fly/10 flex items-center justify-center text-[10px]">3</span>
              <span>STATE SAMPLING</span>
            </div>
            <p className="text-foreground/70 leading-relaxed text-[11px]">
              4,096 virtual electrodes sample internal recurrent state vectors across the connectome at each step.
            </p>
          </div>

          <div className="p-4 border border-paper-border bg-paper-light space-y-2 rounded-sm">
            <div className="flex items-center gap-2 text-fly font-semibold">
              <span className="h-5 w-5 rounded-full bg-fly/10 flex items-center justify-center text-[10px]">4</span>
              <span>DIRECT READOUT</span>
            </div>
            <p className="text-foreground/70 leading-relaxed text-[11px]">
              A multi-output Ridge regression learns to project internal states into multi-step future horizons.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
};
