"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Hero } from "../components/Hero";
import { BrainStats } from "../components/BrainStats";
import { BrainExplainer } from "../components/BrainExplainer";
import { BrainInfo, DemoItem } from "../lib/types";
import { getBrainInfo, getDemos } from "../lib/api";
import { ArrowRight, Sparkles, Activity, Play } from "lucide-react";

export default function LandingPage() {
  const [brainInfo, setBrainInfo] = useState<BrainInfo | null>(null);
  const [demos, setDemos] = useState<DemoItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    Promise.all([
      getBrainInfo().catch(() => null),
      getDemos().catch(() => []),
    ]).then(([bInfo, demoList]) => {
      setBrainInfo(bInfo);
      setDemos(demoList);
      setLoading(false);
    });
  }, []);

  return (
    <div className="space-y-12">
      {/* Hero Section */}
      <Hero />

      {/* Connectome Statistics Bar */}
      <div className="mx-auto max-w-4xl px-4 sm:px-6">
        <BrainStats brainInfo={brainInfo} loading={loading} />
      </div>

      {/* Concept & Process Walkthrough */}
      <BrainExplainer />

      {/* Built-in Benchmark Datasets Preview */}
      <section className="py-8">
        <div className="mx-auto max-w-4xl px-4 sm:px-6 space-y-6">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-3 border-b border-paper-border pb-3">
            <div>
              <span className="font-mono text-xs uppercase tracking-widest text-fly font-bold">
                02 / READY EXPERIMENTS
              </span>
              <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground font-sans mt-1">
                Try a benchmark signal through the connectome
              </h2>
            </div>
            <Link
              href="/experiment"
              className="font-mono text-xs text-fly hover:text-fly-hover uppercase tracking-wider font-semibold inline-flex items-center gap-1"
            >
              <span>Custom CSV Upload</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 font-mono">
            {demos.map((demo) => (
              <div
                key={demo.id}
                className="border border-paper-border bg-paper-light p-5 rounded-sm flex flex-col justify-between space-y-4 hover:border-foreground/40 transition-colors"
              >
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-bold text-foreground">{demo.name}</span>
                    <span className="text-[10px] text-foreground/50 uppercase border border-paper-border px-1.5 py-0.5 rounded">
                      600 steps
                    </span>
                  </div>
                  <p className="text-[11px] text-foreground/70 leading-relaxed font-sans">
                    {demo.description}
                  </p>
                </div>

                <div className="pt-3 border-t border-paper-border/60">
                  <Link
                    href={`/experiment?demo=${demo.id}`}
                    className="w-full inline-flex items-center justify-center gap-2 bg-paper hover:bg-paper-dark border border-paper-border text-foreground font-semibold px-4 py-2 rounded-sm text-xs uppercase tracking-wider transition-colors"
                  >
                    <Play className="h-3 w-3 text-fly" />
                    <span>Run This Signal</span>
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Editorial Final CTA */}
      <section className="py-14 border-t border-paper-border bg-paper-dark/40">
        <div className="mx-auto max-w-3xl px-4 sm:px-6 text-center space-y-6">
          <h2 className="text-2xl sm:text-4xl font-extrabold tracking-tight text-foreground font-sans">
            Does biological wiring outperform classical models?
          </h2>
          <p className="text-sm text-foreground/70 leading-relaxed max-w-xl mx-auto font-sans">
            Every FlyCast run measures real held-out RMSE against persistence and autoregressive baselines.
            If the fly wins, you see it. If the fly loses, we display that honestly.
          </p>
          <div className="pt-2">
            <Link
              href="/experiment"
              className="inline-flex items-center gap-3 bg-fly hover:bg-fly-hover text-white px-8 py-4 rounded-sm font-mono text-xs uppercase tracking-widest font-bold shadow-sm transition-all hover:translate-y-[-1px]"
            >
              <span>LAUNCH EXPERIMENT</span>
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
