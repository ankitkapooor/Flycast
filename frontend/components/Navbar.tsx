"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { getHealth } from "../lib/api";
import { Activity, ShieldCheck, HelpCircle } from "lucide-react";

export const Navbar: React.FC = () => {
  const [brainStatus, setBrainStatus] = useState<string>("checking");

  useEffect(() => {
    getHealth()
      .then((res) => {
        if (res.brain_loaded) setBrainStatus("ready");
        else if (res.status === "initializing") setBrainStatus("initializing");
        else setBrainStatus("offline");
      })
      .catch(() => setBrainStatus("offline"));
  }, []);

  return (
    <header className="sticky top-0 z-40 w-full border-b border-paper-border bg-paper/90 backdrop-blur-sm">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3 sm:px-6">
        {/* Brand */}
        <Link href="/" className="group flex items-baseline gap-2.5">
          <span className="font-mono text-xl font-bold tracking-tighter text-foreground group-hover:text-fly transition-colors">
            FLYCAST
          </span>
          <span className="hidden sm:inline font-mono text-[10px] uppercase tracking-widest text-foreground/50 border border-paper-border px-1.5 py-0.5 rounded">
            MaleCNS v1.0
          </span>
        </Link>

        {/* Navigation & Status */}
        <nav className="flex items-center gap-5 sm:gap-7 font-mono text-xs uppercase tracking-wider">
          <Link
            href="/experiment"
            className="text-foreground/80 hover:text-fly font-medium transition-colors"
          >
            Experiment
          </Link>
          <Link
            href="/method"
            className="text-foreground/80 hover:text-fly transition-colors"
          >
            Methodology
          </Link>
          <Link
            href="/about"
            className="text-foreground/80 hover:text-fly transition-colors"
          >
            About
          </Link>

          {/* Connectome Health Status Pill */}
          <div
            className="flex items-center gap-1.5 border border-paper-border bg-paper-dark/80 px-2.5 py-1 rounded-full text-[11px]"
            title={`Connectome runtime status: ${brainStatus}`}
          >
            <span
              className={`h-2 w-2 rounded-full ${
                brainStatus === "ready"
                  ? "bg-emerald-600 animate-pulse"
                  : brainStatus === "initializing"
                  ? "bg-amber-500 animate-spin"
                  : "bg-red-500"
              }`}
            />
            <span className="text-foreground/70 lowercase">
              {brainStatus === "ready" ? "connectome active" : brainStatus}
            </span>
          </div>
        </nav>
      </div>
    </header>
  );
};
