"use client";

import React, { useEffect, useState } from "react";
import { ActivityVizData } from "../lib/types";

interface ActivityVizProps {
  activityData?: ActivityVizData | null;
  animating?: boolean;
}

export const ActivityViz: React.FC<ActivityVizProps> = ({ activityData, animating = false }) => {
  const [frame, setFrame] = useState<number>(0);

  // If live activity frames are provided, animate through them
  useEffect(() => {
    if (!activityData?.sample_activity || activityData.sample_activity.length === 0) return;
    const interval = setInterval(() => {
      setFrame((prev) => (prev + 1) % activityData.sample_activity.length);
    }, 120);
    return () => clearInterval(interval);
  }, [activityData]);

  // Fallback simulated dots if loading
  const currentSample: number[] =
    activityData?.sample_activity && activityData.sample_activity.length > 0
      ? activityData.sample_activity[frame]
      : Array.from({ length: 64 }, (_, i) => Math.sin(i * 0.3 + Date.now() / 800) * 0.5);

  return (
    <div className="border border-paper-border bg-console-bg p-4 rounded-sm text-console-text font-mono">
      <div className="flex items-center justify-between border-b border-console-border pb-2.5 mb-3 text-[11px]">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-fly animate-pulse" />
          <span className="font-semibold uppercase tracking-wider text-console-text">
            Sampled Simulated Reservoir State
          </span>
        </div>
        <span className="text-[10px] text-console-muted">
          {activityData?.num_sampled_neurons || currentSample.length} virtual electrodes
        </span>
      </div>

      {/* Grid of virtual neuron electrode activity */}
      <div className="grid grid-cols-8 sm:grid-cols-16 gap-1.5 py-2">
        {currentSample.map((val, idx) => {
          const absVal = Math.min(1.0, Math.abs(val));
          // Color intensity based on state activation
          const opacity = Math.max(0.15, absVal);
          const isExcited = absVal > 0.65;

          return (
            <div
              key={idx}
              className="h-3.5 rounded-[1px] transition-all duration-150 flex items-center justify-center text-[8px]"
              style={{
                backgroundColor: isExcited ? `rgba(194, 65, 12, ${opacity})` : `rgba(229, 229, 223, ${opacity * 0.6})`,
              }}
              title={`Neuron #${idx}: magnitude ${val.toFixed(3)}`}
            />
          );
        })}
      </div>

      <div className="mt-2 pt-2 border-t border-console-border flex items-center justify-between text-[10px] text-console-muted">
        <span>Dynamics: Leaky rate reservoir tanh(rec + win)</span>
        <span>Frozen MaleCNS synaptic topology</span>
      </div>
    </div>
  );
};
