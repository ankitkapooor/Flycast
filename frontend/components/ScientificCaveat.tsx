import React from "react";
import { AlertCircle } from "lucide-react";

interface ScientificCaveatProps {
  detailed?: boolean;
  className?: string;
}

export const ScientificCaveat: React.FC<ScientificCaveatProps> = ({ detailed = false, className = "" }) => {
  return (
    <aside
      aria-label="Scientific Limitations Note"
      className={`border-l-2 border-fly/70 bg-paper-dark/60 p-4 font-mono text-xs text-foreground/80 ${className}`}
    >
      <div className="flex items-start gap-2.5">
        <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-fly" />
        <div className="space-y-1">
          <span className="font-semibold tracking-wider text-foreground uppercase">Scientific Caveat</span>
          <p className="leading-relaxed">
            FlyCast uses real anatomical connectivity with engineered neural dynamics. It is not a biological
            simulation of the original fly.
          </p>
          {detailed && (
            <p className="mt-2 text-foreground/70 leading-relaxed">
              The MaleCNS dataset provides structural synaptic topology. Moment-to-moment electrophysiology,
              graded synaptic transmission, neuromodulatory tone, and living cognitive states are not modeled.
              External time-series values stimulate annotated sensory neurons through synthetic input projections.
            </p>
          )}
        </div>
      </div>
    </aside>
  );
};
