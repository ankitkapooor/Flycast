"use client";

import React from "react";
import { ExperimentForm } from "../../components/ExperimentForm";
import { ScientificCaveat } from "../../components/ScientificCaveat";

export default function NewExperimentPage() {
  return (
    <div className="py-10">
      <div className="mx-auto max-w-4xl px-4 sm:px-6 space-y-8">
        {/* Editorial Heading */}
        <div className="border-b border-paper-border pb-4 space-y-1 font-mono">
          <div className="text-[11px] uppercase tracking-widest text-fly font-bold">
            TIME-SERIES TO CONNECTOME MAPPING
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight text-foreground font-sans">
            Configure Your Experiment
          </h1>
          <p className="text-xs text-foreground/70 font-sans leading-relaxed">
            Upload your dataset or select a benchmark. FlyCast will inject your signal across 512 annotated
            sensory neurons, propagate through 166K recurrent nodes, and evaluate held-out forecast accuracy.
          </p>
        </div>

        {/* 3-Stage Form */}
        <ExperimentForm />

        {/* Scientific Caveat */}
        <div className="pt-6">
          <ScientificCaveat detailed={true} />
        </div>
      </div>
    </div>
  );
}
