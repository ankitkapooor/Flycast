import React from "react";
import { ExperimentStatus } from "../lib/types";
import { ActivityViz } from "./ActivityViz";
import { Loader2, Network, Cpu, Zap, Activity } from "lucide-react";

interface ExperimentProgressProps {
  status: ExperimentStatus;
  neurons?: number;
  edges?: number;
}

export const ExperimentProgress: React.FC<ExperimentProgressProps> = ({
  status,
  neurons = 166483,
  edges = 25580000,
}) => {
  return (
    <div className="space-y-6 max-w-3xl mx-auto font-mono">
      {/* Status Header */}
      <div className="border border-paper-border bg-paper-light p-6 rounded-sm space-y-4">
        <div className="flex items-center justify-between border-b border-paper-border pb-3">
          <div className="flex items-center gap-3">
            <Loader2 className="h-5 w-5 text-fly animate-spin" />
            <span className="text-base font-bold text-foreground uppercase tracking-wider">
              {status.status === "queued"
                ? "EXPERIMENT QUEUED"
                : status.status === "preprocessing"
                ? "VALIDATING SIGNAL & NORMALIZING"
                : status.status === "running_brain"
                ? "SIGNAL ENTERING CNS"
                : status.status === "training_readout"
                ? "TRAINING LINEAR READOUT"
                : status.status === "running_baselines"
                ? "EVALUATING BASELINES"
                : status.status === "running_control"
                ? "TESTING WEIGHT-SHUFFLED CONTROL"
                : "FINALIZING RESULTS"}
            </span>
          </div>
          <span className="text-sm font-bold text-fly">{status.progress}%</span>
        </div>

        {/* Progress Bar */}
        <div className="w-full bg-paper-dark h-3 rounded-sm overflow-hidden border border-paper-border">
          <div
            className="bg-fly h-full transition-all duration-300 ease-out"
            style={{ width: `${Math.max(5, status.progress)}%` }}
          />
        </div>

        {/* Stage message */}
        <p className="text-xs text-foreground/80 leading-relaxed">
          {status.message || "Propagating temporal dynamics through recurrent connectome matrix..."}
        </p>
      </div>

      {/* Scale indicators */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
        <div className="border border-paper-border bg-paper-light p-3 rounded-sm space-y-1">
          <div className="flex items-center gap-1.5 text-foreground/60 text-[10px] uppercase">
            <Network className="h-3 w-3" />
            <span>Connected Nodes</span>
          </div>
          <div className="font-bold text-foreground text-sm">{neurons.toLocaleString()}</div>
          <div className="text-[10px] text-foreground/50">recurrent neurons</div>
        </div>

        <div className="border border-paper-border bg-paper-light p-3 rounded-sm space-y-1">
          <div className="flex items-center gap-1.5 text-foreground/60 text-[10px] uppercase">
            <Activity className="h-3 w-3" />
            <span>Synaptic Edges</span>
          </div>
          <div className="font-bold text-foreground text-sm">{(edges / 1e6).toFixed(2)}M</div>
          <div className="text-[10px] text-foreground/50">directed connections</div>
        </div>

        <div className="border border-paper-border bg-paper-light p-3 rounded-sm space-y-1">
          <div className="flex items-center gap-1.5 text-fly text-[10px] uppercase">
            <Zap className="h-3 w-3" />
            <span>Sensory Channels</span>
          </div>
          <div className="font-bold text-fly text-sm">512</div>
          <div className="text-[10px] text-foreground/50">input injection</div>
        </div>

        <div className="border border-paper-border bg-paper-light p-3 rounded-sm space-y-1">
          <div className="flex items-center gap-1.5 text-foreground/60 text-[10px] uppercase">
            <Cpu className="h-3 w-3" />
            <span>Virtual Electrodes</span>
          </div>
          <div className="font-bold text-foreground text-sm">4,096</div>
          <div className="text-[10px] text-foreground/50">sampled readouts</div>
        </div>
      </div>

      {/* Live Simulated Activity Visualization */}
      <ActivityViz animating={true} />
    </div>
  );
};
