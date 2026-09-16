import React from "react";
import { ModelMetrics } from "../lib/types";
import { Trophy, CheckCircle, Award } from "lucide-react";

interface MetricsGridProps {
  flyMetrics: ModelMetrics;
  persistenceMetrics: ModelMetrics;
  arMetrics: ModelMetrics;
  controlMetrics?: ModelMetrics | null;
  winner: string;
}

export const MetricsGrid: React.FC<MetricsGridProps> = ({
  flyMetrics,
  persistenceMetrics,
  arMetrics,
  controlMetrics,
  winner,
}) => {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 font-mono">
      {/* FlyCast Connectome Card */}
      <div
        className={`border p-5 rounded-sm space-y-3 transition-all ${
          winner === "fly"
            ? "border-fly bg-fly/5 ring-1 ring-fly/30 shadow-sm"
            : "border-paper-border bg-paper-light"
        }`}
      >
        <div className="flex items-center justify-between border-b border-paper-border pb-2">
          <div className="flex items-center gap-1.5 font-bold text-xs uppercase tracking-wider text-fly">
            <span>FLYCAST CONNECTOME</span>
            {winner === "fly" && <Award className="h-3.5 w-3.5 text-fly" />}
          </div>
          {winner === "fly" && (
            <span className="text-[10px] bg-fly text-white font-bold px-1.5 py-0.5 rounded">WINNER</span>
          )}
        </div>

        <div className="space-y-2">
          <div>
            <div className="text-[10px] uppercase text-foreground/50">Primary Metric</div>
            <div className="text-2xl font-extrabold text-foreground">
              {flyMetrics.rmse.toFixed(4)}
              <span className="text-xs font-normal text-foreground/50 ml-1">RMSE</span>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-2 pt-2 border-t border-paper-border/60 text-[11px]">
            <div>
              <span className="text-[9px] uppercase text-foreground/50 block">MAE</span>
              <span className="font-semibold text-foreground">{flyMetrics.mae.toFixed(4)}</span>
            </div>
            <div>
              <span className="text-[9px] uppercase text-foreground/50 block">R²</span>
              <span className="font-semibold text-foreground">{flyMetrics.r2.toFixed(3)}</span>
            </div>
            <div>
              <span className="text-[9px] uppercase text-foreground/50 block">sMAPE</span>
              <span className="font-semibold text-foreground">{flyMetrics.smape.toFixed(1)}%</span>
            </div>
          </div>
        </div>
      </div>

      {/* Autoregressive Ridge Baseline Card */}
      <div
        className={`border p-5 rounded-sm space-y-3 transition-all ${
          winner === "autoregressive"
            ? "border-obs-autoregressive bg-teal-50 ring-1 ring-teal-500/30 shadow-sm"
            : "border-paper-border bg-paper-light"
        }`}
      >
        <div className="flex items-center justify-between border-b border-paper-border pb-2">
          <div className="flex items-center gap-1.5 font-bold text-xs uppercase tracking-wider text-obs-autoregressive">
            <span>AUTOREGRESSIVE RIDGE</span>
            {winner === "autoregressive" && <Award className="h-3.5 w-3.5 text-obs-autoregressive" />}
          </div>
          {winner === "autoregressive" && (
            <span className="text-[10px] bg-obs-autoregressive text-white font-bold px-1.5 py-0.5 rounded">WINNER</span>
          )}
        </div>

        <div className="space-y-2">
          <div>
            <div className="text-[10px] uppercase text-foreground/50">Primary Metric</div>
            <div className="text-2xl font-extrabold text-foreground">
              {arMetrics.rmse.toFixed(4)}
              <span className="text-xs font-normal text-foreground/50 ml-1">RMSE</span>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-2 pt-2 border-t border-paper-border/60 text-[11px]">
            <div>
              <span className="text-[9px] uppercase text-foreground/50 block">MAE</span>
              <span className="font-semibold text-foreground">{arMetrics.mae.toFixed(4)}</span>
            </div>
            <div>
              <span className="text-[9px] uppercase text-foreground/50 block">Optimal Lag</span>
              <span className="font-semibold text-foreground">{arMetrics.best_lag || "—"}</span>
            </div>
            <div>
              <span className="text-[9px] uppercase text-foreground/50 block">Alpha</span>
              <span className="font-semibold text-foreground">{arMetrics.best_alpha || "—"}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Persistence Baseline Card */}
      <div
        className={`border p-5 rounded-sm space-y-3 transition-all ${
          winner === "persistence"
            ? "border-obs-persistence bg-slate-100 ring-1 ring-slate-400/30 shadow-sm"
            : "border-paper-border bg-paper-light"
        }`}
      >
        <div className="flex items-center justify-between border-b border-paper-border pb-2">
          <div className="flex items-center gap-1.5 font-bold text-xs uppercase tracking-wider text-obs-persistence">
            <span>PERSISTENCE BASELINE</span>
            {winner === "persistence" && <Award className="h-3.5 w-3.5 text-obs-persistence" />}
          </div>
          {winner === "persistence" && (
            <span className="text-[10px] bg-obs-persistence text-white font-bold px-1.5 py-0.5 rounded">WINNER</span>
          )}
        </div>

        <div className="space-y-2">
          <div>
            <div className="text-[10px] uppercase text-foreground/50">Primary Metric</div>
            <div className="text-2xl font-extrabold text-foreground">
              {persistenceMetrics.rmse.toFixed(4)}
              <span className="text-xs font-normal text-foreground/50 ml-1">RMSE</span>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2 pt-2 border-t border-paper-border/60 text-[11px]">
            <div>
              <span className="text-[9px] uppercase text-foreground/50 block">MAE</span>
              <span className="font-semibold text-foreground">{persistenceMetrics.mae.toFixed(4)}</span>
            </div>
            <div>
              <span className="text-[9px] uppercase text-foreground/50 block">sMAPE</span>
              <span className="font-semibold text-foreground">{persistenceMetrics.smape.toFixed(1)}%</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
