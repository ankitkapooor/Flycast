import React from "react";
import Link from "next/link";

export const Footer: React.FC = () => {
  return (
    <footer className="w-full border-t border-paper-border bg-paper-dark/60 py-10 mt-20 text-xs font-mono text-foreground/70">
      <div className="mx-auto max-w-6xl px-4 sm:px-6 space-y-6">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 pb-6 border-b border-paper-border/60">
          <div>
            <span className="font-bold tracking-tight text-foreground text-sm">FLYCAST</span>
            <p className="mt-1 text-foreground/60 max-w-md">
              A fixed recurrent computational reservoir built directly on the experimentally reconstructed MaleCNS v1.0
              Drosophila connectome.
            </p>
          </div>
          <div className="flex flex-wrap gap-6 text-foreground/80 uppercase text-[11px] tracking-wider">
            <Link href="/experiment" className="hover:text-fly transition-colors">
              Run Experiment
            </Link>
            <Link href="/method" className="hover:text-fly transition-colors">
              Methodology
            </Link>
            <Link href="/about" className="hover:text-fly transition-colors">
              Scientific Notes
            </Link>
            <a
              href="https://github.com/flyem-male-cns"
              target="_blank"
              rel="noreferrer"
              className="hover:text-fly transition-colors"
            >
              MaleCNS Source
            </a>
          </div>
        </div>

        <div className="text-[11px] leading-relaxed text-foreground/60 space-y-2">
          <p>
            Connectome data source: <strong>MaleCNS v1.0</strong>, an open-access collaboration by HHMI Janelia FlyEM,
            University of Cambridge, MRC Laboratory of Molecular Biology, and Google Research (licensed under CC BY).
            FlyCast is an independent computational project and does not imply endorsement by these institutions.
          </p>
          <p>
            Application Code &copy; {new Date().getFullYear()} FlyCast Authors. MIT License.
          </p>
        </div>
      </div>
    </footer>
  );
};
