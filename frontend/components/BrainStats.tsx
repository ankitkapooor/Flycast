import React from "react";
import { BrainInfo } from "../lib/types";
import { formatNumber } from "../lib/formatting";
import { Network, Cpu, Zap, Activity } from "lucide-react";

interface BrainStatsProps {
  brainInfo?: BrainInfo | null;
  loading?: boolean;
}

export const BrainStats: React.FC<BrainStatsProps> = ({ brainInfo, loading }) => {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 border border-paper-border bg-paper-light p-4 rounded-sm font-mono text-xs">
      <div className="space-y-1">
        <div className="flex items-center gap-1.5 text-foreground/60 uppercase text-[10px] tracking-wider">
          <Network className="h-3.5 w-3.5 text-foreground/50" />
          <span>Published CNS Neurons</span>
        </div>
        <div className="text-lg font-bold text-foreground">
          {loading ? "..." : formatNumber(brainInfo?.published_neurons || 166691)}
        </div>
        <div className="text-[10px] text-foreground/50">
          Runtime: {loading ? "..." : formatNumber(brainInfo?.runtime_neurons || 166483)} nodes
        </div>
      </div>

      <div className="space-y-1">
        <div className="flex items-center gap-1.5 text-foreground/60 uppercase text-[10px] tracking-wider">
          <Activity className="h-3.5 w-3.5 text-foreground/50" />
          <span>Structural Synapses</span>
        </div>
        <div className="text-lg font-bold text-foreground">
          {loading ? "..." : formatNumber(brainInfo?.runtime_edges || 25580000)}
        </div>
        <div className="text-[10px] text-foreground/50">W[post, pre] sparse CSR</div>
      </div>

      <div className="space-y-1">
        <div className="flex items-center gap-1.5 text-foreground/60 uppercase text-[10px] tracking-wider">
          <Zap className="h-3.5 w-3.5 text-fly" />
          <span>Sensory Inputs</span>
        </div>
        <div className="text-lg font-bold text-fly">
          {loading ? "..." : formatNumber(brainInfo?.input_neurons || 512)}
        </div>
        <div className="text-[10px] text-foreground/50">Annotated sensory bodies</div>
      </div>

      <div className="space-y-1">
        <div className="flex items-center gap-1.5 text-foreground/60 uppercase text-[10px] tracking-wider">
          <Cpu className="h-3.5 w-3.5 text-foreground/50" />
          <span>Readout Electrodes</span>
        </div>
        <div className="text-lg font-bold text-foreground">
          {loading ? "..." : formatNumber(brainInfo?.readout_neurons || 4096)}
        </div>
        <div className="text-[10px] text-foreground/50">Linear Ridge mapping</div>
      </div>
    </div>
  );
};
