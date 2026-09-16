import React from "react";
import { EditorialVerdict, ModelMetrics } from "../lib/types";
import { Scale, Shuffle, CheckCircle, XCircle, MinusCircle } from "lucide-react";

interface BaselineComparisonProps {
  editorial: EditorialVerdict;
  flyMetrics: ModelMetrics;
  persistenceMetrics: ModelMetrics;
  arMetrics: ModelMetrics;
  control?: {
    type: string;
    metrics: ModelMetrics;
    future_forecast: number[];
  } | null;
}

export const BaselineComparison: React.FC<BaselineComparisonProps> = ({
  editorial,
  flyMetrics,
  persistenceMetrics,
  arMetrics,
  control,
}) => {
  const isFlyWinner = editorial.winner === "fly";
  const isTie = editorial.verdict.includes("tied");

  return (
    <div className="space-y-6 font-mono text-xs">
      {/* Editorial Section: DID THE BRAIN HELP? */}
      <div className="border border-paper-border bg-paper-light p-6 rounded-sm space-y-4">
        <div className="flex items-center gap-2 text-foreground/60 text-[11px] uppercase tracking-wider border-b border-paper-border pb-2">
          <Scale className="h-4 w-4 text-fly" />
          <span>Evaluation / Did The Brain Help?</span>
        </div>

        <div className="space-y-2">
          <div className="flex items-center gap-2.5">
            {isFlyWinner ? (
              <CheckCircle className="h-5 w-5 text-fly shrink-0" />
            ) : isTie ? (
              <MinusCircle className="h-5 w-5 text-amber-600 shrink-0" />
            ) : (
              <XCircle className="h-5 w-5 text-foreground/50 shrink-0" />
            )}
            <h3 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground font-sans">
              {editorial.headline}
            </h3>
          </div>

          <p className="text-foreground/80 text-sm leading-relaxed font-sans pt-1">
            {editorial.summary}
          </p>
        </div>

        {/* Detailed Comparison Table */}
        <div className="pt-2 border-t border-paper-border/60">
          <div className="grid grid-cols-3 gap-2 py-1 text-[11px] text-foreground/60 uppercase font-semibold">
            <span>Model</span>
            <span className="text-center">Held-Out RMSE</span>
            <span className="text-right">vs Connectome</span>
          </div>
          <div className="divide-y divide-paper-border/40 text-[11px]">
            <div className="grid grid-cols-3 gap-2 py-2 font-bold text-fly">
              <span>Fly Connectome</span>
              <span className="text-center">{flyMetrics.rmse.toFixed(4)}</span>
              <span className="text-right font-normal text-foreground/50">—</span>
            </div>
            <div className="grid grid-cols-3 gap-2 py-2 text-obs-autoregressive">
              <span>Autoregressive Ridge</span>
              <span className="text-center font-bold">{arMetrics.rmse.toFixed(4)}</span>
              <span className="text-right">
                {arMetrics.rmse > flyMetrics.rmse ? (
                  <span className="text-fly">+{ (arMetrics.rmse - flyMetrics.rmse).toFixed(4) } (fly won)</span>
                ) : (
                  <span className="text-obs-autoregressive">{ (arMetrics.rmse - flyMetrics.rmse).toFixed(4) } (AR won)</span>
                )}
              </span>
            </div>
            <div className="grid grid-cols-3 gap-2 py-2 text-obs-persistence">
              <span>Persistence (Naive)</span>
              <span className="text-center font-bold">{persistenceMetrics.rmse.toFixed(4)}</span>
              <span className="text-right">
                {persistenceMetrics.rmse > flyMetrics.rmse ? (
                  <span className="text-fly">+{ (persistenceMetrics.rmse - flyMetrics.rmse).toFixed(4) }</span>
                ) : (
                  <span className="text-obs-persistence">{ (persistenceMetrics.rmse - flyMetrics.rmse).toFixed(4) }</span>
                )}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Control Comparison: DOES THE REAL WIRING MATTER? */}
      {control && (
        <div className="border border-paper-border bg-paper-light p-6 rounded-sm space-y-4">
          <div className="flex items-center gap-2 text-foreground/60 text-[11px] uppercase tracking-wider border-b border-paper-border pb-2">
            <Shuffle className="h-4 w-4 text-obs-control" />
            <span>Scientific Control / Does The Real Wiring Matter?</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="p-3 border border-paper-border bg-paper rounded-sm space-y-1">
              <span className="text-[10px] uppercase text-foreground/50 block">Real Connectome Wiring</span>
              <div className="text-xl font-bold text-fly">{flyMetrics.rmse.toFixed(4)}</div>
              <div className="text-[10px] text-foreground/50">Observed synaptic contact counts</div>
            </div>

            <div className="p-3 border border-paper-border bg-paper rounded-sm space-y-1">
              <span className="text-[10px] uppercase text-foreground/50 block">Weight-Shuffled Wiring</span>
              <div className="text-xl font-bold text-foreground">{control.metrics.rmse.toFixed(4)}</div>
              <div className="text-[10px] text-foreground/50">Same topology, permuted magnitudes</div>
            </div>
          </div>

          <p className="text-foreground/80 leading-relaxed font-sans text-xs">
            {editorial.control_summary ||
              "The control preserves identical graph topology, numbers of neurons, and edge counts, but scrambles connection strengths. This isolates whether observed synaptic weights explain performance."}
          </p>
        </div>
      )}
    </div>
  );
};
