"use client";

import React, { useState } from "react";
import { ExperimentResultPayload } from "../lib/types";
import { getPredictionsCsvUrl, getExperimentJsonUrl } from "../lib/api";
import { Download, Copy, Check, ChevronDown, ChevronUp, Clock, Terminal } from "lucide-react";

interface TechnicalDetailsProps {
  result: ExperimentResultPayload;
}

export const TechnicalDetails: React.FC<TechnicalDetailsProps> = ({ result }) => {
  const [copiedShare, setCopiedShare] = useState<boolean>(false);
  const [panelOpen, setPanelOpen] = useState<boolean>(false);

  const bestBaselineName =
    result.editorial.winner === "autoregressive" ? "Autoregressive Ridge" : "Persistence";
  const bestBaselineRmse =
    result.editorial.winner === "autoregressive"
      ? result.baselines.autoregressive_ridge.rmse
      : result.baselines.persistence.rmse;

  const shareText = `I ran ${result.dataset.target} through a 166K-neuron fruit-fly connectome.\nFlyCast RMSE: ${result.fly.rmse.toFixed(
    4
  )}\nBest baseline: ${bestBaselineRmse.toFixed(4)} (${bestBaselineName})\n${result.editorial.verdict}`;

  const handleCopyShare = () => {
    navigator.clipboard.writeText(shareText);
    setCopiedShare(true);
    setTimeout(() => setCopiedShare(false), 2000);
  };

  return (
    <div className="space-y-8 font-mono text-xs">
      {/* WHAT JUST HAPPENED? Section 51 */}
      <section className="border border-paper-border bg-paper-light p-6 rounded-sm space-y-4">
        <span className="text-[11px] uppercase tracking-widest text-fly font-bold block">
          03 / EXECUTION WALKTHROUGH
        </span>
        <h3 className="text-xl font-bold tracking-tight text-foreground font-sans">
          What just happened inside the connectome?
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 pt-2 text-[11px] leading-relaxed text-foreground/80">
          <div className="p-3.5 bg-paper rounded border border-paper-border space-y-1">
            <span className="font-bold text-fly block">1. Signal Standardization</span>
            <p>
              Your time-series values were normalized using parameters fitted strictly on chronological training rows.
            </p>
          </div>

          <div className="p-3.5 bg-paper rounded border border-paper-border space-y-1">
            <span className="font-bold text-fly block">2. Sensory Projection</span>
            <p>
              Each observation stimulated {result.reservoir.input_neurons} annotated sensory neurons via deterministic
              projections.
            </p>
          </div>

          <div className="p-3.5 bg-paper rounded border border-paper-border space-y-1">
            <span className="font-bold text-fly block">3. Recurrent Propagation</span>
            <p>
              Activity rippled through {result.reservoir.edges.toLocaleString()} synaptic edges under leaky tanh rate
              dynamics.
            </p>
          </div>

          <div className="p-3.5 bg-paper rounded border border-paper-border space-y-1">
            <span className="font-bold text-fly block">4. Reservoir Sampling</span>
            <p>
              {result.reservoir.readout_neurons} virtual electrodes recorded temporal reservoir state vectors at every
              timestep.
            </p>
          </div>

          <div className="p-3.5 bg-paper rounded border border-paper-border space-y-1">
            <span className="font-bold text-fly block">5. Ridge Readout</span>
            <p>
              A linear Ridge model (alpha={result.reservoir.ridge_alpha}) learned multi-horizon direct forecasts without
              altering the brain.
            </p>
          </div>

          <div className="p-3.5 bg-paper rounded border border-paper-border space-y-1">
            <span className="font-bold text-fly block">6. Held-Out Evaluation</span>
            <p>
              Forecast accuracy was benchmarked on unseen test observations and compared against persistence and
              autoregression.
            </p>
          </div>
        </div>
      </section>

      {/* Share & Download Actions */}
      <section className="flex flex-wrap items-center justify-between gap-4 p-4 border border-paper-border bg-paper-light rounded-sm">
        <div className="flex flex-wrap items-center gap-3">
          <a
            href={getPredictionsCsvUrl(result.experiment_id)}
            download
            className="inline-flex items-center gap-2 px-4 py-2 border border-paper-border bg-paper hover:bg-paper-dark text-foreground font-semibold rounded-sm transition-colors text-[11px]"
          >
            <Download className="h-3.5 w-3.5 text-fly" />
            <span>DOWNLOAD FORECAST CSV</span>
          </a>

          <a
            href={getExperimentJsonUrl(result.experiment_id)}
            download
            className="inline-flex items-center gap-2 px-4 py-2 border border-paper-border bg-paper hover:bg-paper-dark text-foreground font-semibold rounded-sm transition-colors text-[11px]"
          >
            <Download className="h-3.5 w-3.5 text-foreground/50" />
            <span>DOWNLOAD EXPERIMENT JSON</span>
          </a>
        </div>

        <button
          onClick={handleCopyShare}
          className="inline-flex items-center gap-2 px-4 py-2 border border-fly/40 bg-fly/5 hover:bg-fly/10 text-fly font-bold rounded-sm transition-colors text-[11px]"
        >
          {copiedShare ? <Check className="h-3.5 w-3.5 text-fly" /> : <Copy className="h-3.5 w-3.5 text-fly" />}
          <span>{copiedShare ? "COPIED RESULT" : "COPY SHARE TEXT"}</span>
        </button>
      </section>

      {/* Collapsible Reproducibility Panel (Section 52) */}
      <section className="border border-paper-border bg-paper-light rounded-sm overflow-hidden">
        <button
          onClick={() => setPanelOpen(!panelOpen)}
          className="w-full flex items-center justify-between p-4 bg-paper-dark/50 hover:bg-paper-dark transition-colors text-left"
        >
          <div className="flex items-center gap-2 font-bold uppercase tracking-wider text-[11px] text-foreground">
            <Terminal className="h-4 w-4 text-foreground/60" />
            <span>REPRODUCIBILITY & SYSTEM METADATA</span>
          </div>
          {panelOpen ? <ChevronUp className="h-4 w-4 text-foreground/60" /> : <ChevronDown className="h-4 w-4 text-foreground/60" />}
        </button>

        {panelOpen && (
          <div className="p-6 space-y-4 border-t border-paper-border text-[11px]">
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-y-3 gap-x-6">
              <div>
                <span className="text-foreground/50 block">Experiment ID:</span>
                <span className="text-foreground font-bold break-all">{result.experiment_id}</span>
              </div>
              <div>
                <span className="text-foreground/50 block">Dataset SHA256:</span>
                <span className="text-foreground break-all">{result.reproducibility.dataset_sha256}</span>
              </div>
              <div>
                <span className="text-foreground/50 block">Connectome Version:</span>
                <span className="text-foreground">{result.reproducibility.connectome_version}</span>
              </div>
              <div>
                <span className="text-foreground/50 block">Manifest SHA256:</span>
                <span className="text-foreground break-all">{result.reproducibility.brain_manifest_hash}</span>
              </div>
              <div>
                <span className="text-foreground/50 block">Random Seed:</span>
                <span className="text-foreground">{result.reproducibility.seed}</span>
              </div>
              <div>
                <span className="text-foreground/50 block">Reservoir Leak:</span>
                <span className="text-foreground">{result.reservoir.leak}</span>
              </div>
              <div>
                <span className="text-foreground/50 block">Recurrent Gain:</span>
                <span className="text-foreground">{result.reservoir.recurrent_gain}</span>
              </div>
              <div>
                <span className="text-foreground/50 block">Input Gain:</span>
                <span className="text-foreground">{result.reservoir.input_gain}</span>
              </div>
              <div>
                <span className="text-foreground/50 block">Washout Steps:</span>
                <span className="text-foreground">{result.reservoir.washout}</span>
              </div>
              <div>
                <span className="text-foreground/50 block">Ridge Regularization (Alpha):</span>
                <span className="text-foreground">{result.reservoir.ridge_alpha}</span>
              </div>
              <div>
                <span className="text-foreground/50 block">Train / Val / Test Split:</span>
                <span className="text-foreground">
                  {result.reproducibility.train_size} / {result.reproducibility.val_size} /{" "}
                  {result.reproducibility.test_size}
                </span>
              </div>
              <div>
                <span className="text-foreground/50 block">Simulated Steps:</span>
                <span className="text-foreground">{result.dataset.rows_simulated}</span>
              </div>
            </div>

            {/* Execution Timings (Section 94) */}
            {result.timings && (
              <div className="pt-3 border-t border-paper-border/60">
                <div className="flex items-center gap-1.5 text-foreground/50 mb-2">
                  <Clock className="h-3 w-3" />
                  <span>Execution Profiling:</span>
                </div>
                <div className="flex flex-wrap gap-4 text-foreground/70">
                  <span>Preprocessing: {result.timings.preprocessing_seconds}s</span>
                  <span>Connectome Simulation: {result.timings.reservoir_seconds}s</span>
                  <span>Readout Training: {result.timings.readout_seconds}s</span>
                  <span>Baselines: {result.timings.baseline_seconds}s</span>
                  {result.timings.control_seconds !== undefined && (
                    <span>Control: {result.timings.control_seconds}s</span>
                  )}
                  <span className="font-bold text-foreground">Total: {result.timings.total_seconds}s</span>
                </div>
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  );
};
