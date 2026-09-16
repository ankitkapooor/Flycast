"use client";

import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ExperimentStatus, FullExperimentResponse } from "../../../lib/types";
import { getExperimentStatus, getExperimentResults } from "../../../lib/api";
import { ExperimentProgress } from "../../../components/ExperimentProgress";
import { ForecastChart } from "../../../components/ForecastChart";
import { MetricsGrid } from "../../../components/MetricsGrid";
import { BaselineComparison } from "../../../components/BaselineComparison";
import { TechnicalDetails } from "../../../components/TechnicalDetails";
import { ScientificCaveat } from "../../../components/ScientificCaveat";
import { AlertCircle, ArrowLeft, RefreshCw } from "lucide-react";

export default function ExperimentPage() {
  const params = useParams();
  const expId = params.id as string;

  const [status, setStatus] = useState<ExperimentStatus | null>(null);
  const [resultsData, setResultsData] = useState<FullExperimentResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!expId) return;

    let isSubscribed = true;
    const interval = setInterval(async () => {
      try {
        const st = await getExperimentStatus(expId);
        if (!isSubscribed) return;
        setStatus(st);

        if (st.status === "complete") {
          clearInterval(interval);
          const fullRes = await getExperimentResults(expId);
          if (isSubscribed) {
            setResultsData(fullRes);
          }
        } else if (st.status === "failed") {
          clearInterval(interval);
          setError(st.error || "Experiment execution failed.");
        }
      } catch (err: any) {
        console.error("Polling error:", err);
      }
    }, 1000);

    return () => {
      isSubscribed = false;
      clearInterval(interval);
    };
  }, [expId]);

  // Loading initial status
  if (!status && !error) {
    return (
      <div className="py-20 text-center font-mono space-y-4">
        <RefreshCw className="h-6 w-6 animate-spin mx-auto text-fly" />
        <p className="text-xs text-foreground/70">Connecting to CNS reservoir worker...</p>
      </div>
    );
  }

  // Failed state
  if (error || status?.status === "failed") {
    return (
      <div className="py-16 max-w-2xl mx-auto px-4 font-mono space-y-6">
        <div className="p-6 border border-red-300 bg-red-50 rounded-sm space-y-4">
          <div className="flex items-center gap-2.5 text-red-800 font-bold">
            <AlertCircle className="h-5 w-5 text-red-600" />
            <span>Experiment Failed</span>
          </div>
          <p className="text-xs text-red-700 leading-relaxed font-sans">
            {error || status?.error || "The connectome simulation encountered an error."}
          </p>
          <div className="pt-2">
            <Link
              href="/experiment"
              className="inline-flex items-center gap-2 text-xs bg-red-700 text-white px-4 py-2 rounded-sm font-semibold uppercase hover:bg-red-800 transition-colors"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              <span>Try Another Dataset</span>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // Processing state
  if (status?.status !== "complete" || !resultsData) {
    return (
      <div className="py-12 px-4 sm:px-6">
        <div className="mx-auto max-w-3xl mb-8 font-mono text-xs text-foreground/60 flex items-center justify-between border-b border-paper-border pb-3">
          <span>EXPERIMENT ID: {expId}</span>
          <span className="uppercase text-fly font-bold">{status?.status}</span>
        </div>
        <ExperimentProgress status={status!} />
      </div>
    );
  }

  // Completed State: Show comprehensive results
  const res = resultsData.result;
  const chart = resultsData.chart;

  return (
    <div className="py-10">
      <div className="mx-auto max-w-4xl px-4 sm:px-6 space-y-10">
        {/* Navigation & Experiment Meta Header */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-paper-border pb-4 font-mono text-xs">
          <Link
            href="/experiment"
            className="inline-flex items-center gap-1.5 text-foreground/70 hover:text-fly transition-colors"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            <span>New Experiment</span>
          </Link>
          <div className="flex items-center gap-3 text-[11px] text-foreground/60">
            <span>ID: <strong className="text-foreground">{expId.slice(0, 8)}...</strong></span>
            <span>Target: <strong className="text-fly">{res.dataset.target}</strong></span>
            <span>Simulated Steps: <strong className="text-foreground">{res.dataset.rows_simulated}</strong></span>
          </div>
        </div>

        {/* Resampling Note if applicable (Section 18) */}
        {res.dataset.resampling_note && (
          <div className="p-3 border border-amber-300 bg-amber-50 text-amber-900 text-xs font-mono rounded-sm">
            {res.dataset.resampling_note}
          </div>
        )}

        {/* Large Time-Series Chart (Section 47) */}
        <section className="space-y-3">
          <ForecastChart
            historyPoints={chart.history}
            testPoints={chart.test}
            futurePoints={chart.future}
            targetName={res.dataset.target}
          />
        </section>

        {/* Scorecards Grid (Section 48) */}
        <section className="space-y-2">
          <MetricsGrid
            flyMetrics={res.fly}
            persistenceMetrics={res.baselines.persistence}
            arMetrics={res.baselines.autoregressive_ridge}
            controlMetrics={res.control?.metrics}
            winner={res.winner}
          />
        </section>

        {/* DID THE BRAIN HELP? & Scientific Control (Section 49, 50) */}
        <section className="space-y-4">
          <BaselineComparison
            editorial={res.editorial}
            flyMetrics={res.fly}
            persistenceMetrics={res.baselines.persistence}
            arMetrics={res.baselines.autoregressive_ridge}
            control={res.control}
          />
        </section>

        {/* Technical Details, Explainer & Downloads (Section 51, 52) */}
        <section className="space-y-4">
          <TechnicalDetails result={res} />
        </section>

        {/* Scientific Caveat Component (Section 55) */}
        <div className="pt-4">
          <ScientificCaveat detailed={true} />
        </div>
      </div>
    </div>
  );
}
