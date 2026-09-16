import React, { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { DemoItem } from "../lib/types";
import { getDemos, getDemoCsv, submitExperiment } from "../lib/api";
import { DatasetPreview } from "./DatasetPreview";
import { Upload, FileText, ArrowRight, Check, AlertTriangle, Sparkles, Loader2 } from "lucide-react";

export const ExperimentForm: React.FC = () => {
  const router = useRouter();

  // Demos & Selection State
  const [demos, setDemos] = useState<DemoItem[]>([]);
  const [selectedDemoId, setSelectedDemoId] = useState<string | null>(null);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [csvContent, setCsvContent] = useState<string>("");

  // Parsed CSV structure for Stage 2
  const [headers, setHeaders] = useState<string[]>([]);
  const [previewRows, setPreviewRows] = useState<string[][]>([]);
  const [totalRows, setTotalRows] = useState<number>(0);

  // User configuration
  const [timeCol, setTimeCol] = useState<string>("");
  const [targetCol, setTargetCol] = useState<string>("");
  const [additionalFeatures, setAdditionalFeatures] = useState<string[]>([]);
  const [forecastHorizon, setForecastHorizon] = useState<number>(5);
  const [runControl, setRunControl] = useState<boolean>(false);

  // Form submission state
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load demos on mount
  useEffect(() => {
    getDemos()
      .then((d) => setDemos(d))
      .catch((e) => console.error("Error fetching demos:", e));
  }, []);

  // Parse raw CSV string into preview structure
  const parseCsvText = (text: string) => {
    try {
      const lines = text.trim().split(/\r?\n/);
      if (lines.length < 2) {
        throw new Error("CSV contains insufficient lines.");
      }

      // Infer delimiter
      const firstLine = lines[0];
      const delimiter = firstLine.includes("\t") ? "\t" : firstLine.includes(";") ? ";" : ",";
      const rawHeaders = firstLine.split(delimiter).map((h) => h.trim().replace(/^["']|["']$/g, ""));

      const rows: string[][] = [];
      for (let i = 1; i < Math.min(lines.length, 9); i++) {
        if (!lines[i].trim()) continue;
        const cells = lines[i].split(delimiter).map((c) => c.trim().replace(/^["']|["']$/g, ""));
        rows.push(cells);
      }

      setHeaders(rawHeaders);
      setPreviewRows(rows);
      setTotalRows(lines.length - 1);

      // Auto-detect time and target candidates
      const timeCandidate = rawHeaders.find((h) =>
        /time|date|timestamp|year|epoch|step/i.test(h)
      ) || rawHeaders[0];

      // Target candidate: numeric column not equal to time
      const targetCandidate = rawHeaders.find(
        (h) => h !== timeCandidate && /target|close|price|val|signal|y|x/i.test(h)
      ) || rawHeaders.find((h) => h !== timeCandidate) || rawHeaders[0];

      setTimeCol(timeCandidate);
      setTargetCol(targetCandidate);
      setAdditionalFeatures([]);
      setErrorMsg(null);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to parse CSV file.");
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > 5 * 1024 * 1024) {
      setErrorMsg("File exceeds maximum allowed size of 5 MB.");
      return;
    }

    setUploadedFile(file);
    setSelectedDemoId(null);

    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target?.result as string;
      setCsvContent(content);
      parseCsvText(content);
    };
    reader.readAsText(file);
  };

  const handleSelectDemo = async (demoId: string) => {
    try {
      setSelectedDemoId(demoId);
      setUploadedFile(null);
      setErrorMsg(null);

      const demo = demos.find((d) => d.id === demoId);
      const csvText = await getDemoCsv(demoId);
      setCsvContent(csvText);
      parseCsvText(csvText);

      if (demo) {
        setTimeCol(demo.time_column);
        setTargetCol(demo.target_column);
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Could not load demo CSV.");
    }
  };

  const toggleFeature = (col: string) => {
    if (additionalFeatures.includes(col)) {
      setAdditionalFeatures(additionalFeatures.filter((f) => f !== col));
    } else {
      if (additionalFeatures.length >= 4) {
        // Max 5 total features including target
        return;
      }
      setAdditionalFeatures([...additionalFeatures, col]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!csvContent && !selectedDemoId) {
      setErrorMsg("Please upload a CSV or select an example dataset.");
      return;
    }
    if (totalRows < 100) {
      setErrorMsg("The fly needs more history. Upload at least 100 usable observations.");
      return;
    }
    if (!targetCol) {
      setErrorMsg("Please select a target numeric column to forecast.");
      return;
    }

    setSubmitting(true);
    setErrorMsg(null);

    try {
      const formData = new FormData();
      if (uploadedFile) {
        formData.append("file", uploadedFile);
      } else if (selectedDemoId) {
        formData.append("demo_id", selectedDemoId);
      }

      formData.append("time_column", timeCol);
      formData.append("target_column", targetCol);
      if (additionalFeatures.length > 0) {
        formData.append("feature_columns", additionalFeatures.join(","));
      }
      formData.append("forecast_horizon", forecastHorizon.toString());
      formData.append("run_control", runControl ? "true" : "false");

      const res = await submitExperiment(formData);
      router.push(`/experiment/${res.id}`);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to submit experiment.");
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-10 max-w-3xl mx-auto font-mono">
      {/* STAGE 1: DATA SELECTION */}
      <section className="space-y-4 border border-paper-border bg-paper-light p-6 rounded-sm">
        <div className="flex items-center justify-between border-b border-paper-border pb-3">
          <span className="text-xs uppercase tracking-widest font-bold text-foreground">
            01 / SELECT DATA
          </span>
          <span className="text-[11px] text-foreground/60">Upload CSV or use built-in system</span>
        </div>

        {/* Drag & Drop Upload Box */}
        <div
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-sm p-8 text-center cursor-pointer transition-all ${
            uploadedFile
              ? "border-fly bg-fly/5"
              : "border-paper-border hover:border-foreground/50 hover:bg-paper-dark/50"
          }`}
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept=".csv,text/csv,text/plain"
            className="hidden"
          />
          <div className="flex flex-col items-center gap-2">
            <Upload className={`h-8 w-8 ${uploadedFile ? "text-fly" : "text-foreground/40"}`} />
            <div className="text-sm font-semibold text-foreground">
              {uploadedFile ? uploadedFile.name : "Drop a time-series CSV or click to browse"}
            </div>
            <p className="text-[11px] text-foreground/60">
              Up to 5 MB &bull; Minimum 100 observations &bull; Plain CSV
            </p>
          </div>
        </div>

        {/* Demo Selection Buttons */}
        <div className="space-y-2 pt-2">
          <div className="text-[11px] uppercase tracking-wider text-foreground/60">
            or try a synthetic benchmark:
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
            {demos.map((demo) => {
              const isSelected = selectedDemoId === demo.id;
              return (
                <button
                  type="button"
                  key={demo.id}
                  onClick={() => handleSelectDemo(demo.id)}
                  className={`p-3 text-left border rounded-sm transition-all ${
                    isSelected
                      ? "border-fly bg-fly/10 text-foreground font-bold"
                      : "border-paper-border bg-paper hover:bg-paper-dark text-foreground/80"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold">{demo.name}</span>
                    {isSelected && <Check className="h-3.5 w-3.5 text-fly" />}
                  </div>
                  <p className="text-[10px] text-foreground/60 mt-1 line-clamp-2 leading-tight">
                    {demo.description}
                  </p>
                </button>
              );
            })}
          </div>
        </div>
      </section>

      {/* STAGE 2: INTERPRET & CONFIGURE (Only visible once data is loaded) */}
      {headers.length > 0 && (
        <section className="space-y-6 border border-paper-border bg-paper-light p-6 rounded-sm">
          <div className="flex items-center justify-between border-b border-paper-border pb-3">
            <span className="text-xs uppercase tracking-widest font-bold text-foreground">
              02 / CONFIGURE VARIABLES
            </span>
            <span className="text-[11px] text-foreground/60">
              {totalRows.toLocaleString()} rows &bull; {headers.length} columns
            </span>
          </div>

          {/* Column selectors */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div className="space-y-1.5">
              <label htmlFor="time-column-select" className="block text-[11px] uppercase text-foreground/70 font-semibold">
                Time / Date Column
              </label>
              <select
                id="time-column-select"
                value={timeCol}
                onChange={(e) => setTimeCol(e.target.value)}
                className="w-full bg-paper border border-paper-border p-2 rounded-sm text-foreground focus:outline-none focus:border-fly"
              >
                {headers.map((h) => (
                  <option key={h} value={h}>
                    {h}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-1.5">
              <label htmlFor="target-column-select" className="block text-[11px] uppercase text-fly font-semibold">
                Target Column to Predict ★
              </label>
              <select
                id="target-column-select"
                value={targetCol}
                onChange={(e) => setTargetCol(e.target.value)}
                className="w-full bg-paper border border-fly/60 p-2 rounded-sm text-foreground font-bold focus:outline-none focus:border-fly"
              >
                {headers
                  .filter((h) => h !== timeCol)
                  .map((h) => (
                    <option key={h} value={h}>
                      {h}
                    </option>
                  ))}
              </select>
            </div>
          </div>

          {/* Additional Input Features */}
          {headers.length > 2 && (
            <div className="space-y-2 pt-1 text-xs">
              <span className="block text-[11px] uppercase text-foreground/70 font-semibold">
                Additional Input Signals (Optional, up to 4)
              </span>
              <div className="flex flex-wrap gap-2">
                {headers
                  .filter((h) => h !== timeCol && h !== targetCol)
                  .map((h) => {
                    const isChecked = additionalFeatures.includes(h);
                    return (
                      <button
                        type="button"
                        key={h}
                        onClick={() => toggleFeature(h)}
                        className={`px-2.5 py-1 text-[11px] border rounded-sm transition-colors ${
                          isChecked
                            ? "bg-foreground text-paper border-foreground"
                            : "bg-paper border-paper-border text-foreground/70 hover:border-foreground/40"
                        }`}
                      >
                        {isChecked ? `✓ ${h}` : `+ ${h}`}
                      </button>
                    );
                  })}
              </div>
            </div>
          )}

          {/* Forecast Horizon */}
          <div className="space-y-2 pt-2 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-[11px] uppercase text-foreground/70 font-semibold">
                Forecast Horizon
              </span>
              <span className="font-bold text-fly text-sm">{forecastHorizon} steps</span>
            </div>
            <input
              type="range"
              min={1}
              max={20}
              value={forecastHorizon}
              aria-label="Forecast Horizon"
              onChange={(e) => setForecastHorizon(parseInt(e.target.value, 10))}
              className="w-full accent-fly cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-foreground/40">
              <span>1 step</span>
              <span>10 steps</span>
              <span>20 steps</span>
            </div>
          </div>

          {/* Scientific Control Toggle (Section 23) */}
          <div className="pt-2 border-t border-paper-border/60">
            <label className="flex items-start gap-3 cursor-pointer p-2.5 border border-paper-border rounded-sm hover:bg-paper-dark/40 transition-colors">
              <input
                type="checkbox"
                checked={runControl}
                onChange={(e) => setRunControl(e.target.checked)}
                className="mt-0.5 accent-fly h-4 w-4 rounded"
              />
              <div className="text-xs space-y-0.5">
                <span className="font-bold text-foreground">Run connectome control (weight-shuffled)</span>
                <p className="text-[11px] text-foreground/60 leading-relaxed">
                  Takes longer, but tests whether the real wiring matters by permuting synaptic weights across the
                  exact same graph topology.
                </p>
              </div>
            </label>
          </div>

          {/* Table Preview */}
          <DatasetPreview
            headers={headers}
            rows={previewRows}
            totalRows={totalRows}
            timeColumn={timeCol}
            targetColumn={targetCol}
          />
        </section>
      )}

      {/* Error Notice */}
      {errorMsg && (
        <div className="p-4 border border-red-300 bg-red-50 text-red-800 text-xs rounded-sm flex items-start gap-2.5">
          <AlertTriangle className="h-4 w-4 text-red-600 shrink-0 mt-0.5" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* STAGE 3: RUN BUTTON */}
      {headers.length > 0 && (
        <div className="text-center pt-2">
          <button
            type="submit"
            disabled={submitting}
            className="w-full sm:w-auto inline-flex items-center justify-center gap-3 bg-fly hover:bg-fly-hover disabled:bg-foreground/30 text-white px-10 py-4 rounded-sm font-mono text-sm uppercase tracking-widest font-bold shadow-sm transition-all hover:translate-y-[-1px]"
          >
            {submitting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>INJECTING SIGNAL...</span>
              </>
            ) : (
              <>
                <span>RUN THROUGH THE BRAIN</span>
                <ArrowRight className="h-4 w-4" />
              </>
            )}
          </button>
          <div className="mt-2 text-[10px] text-foreground/50">
            Propagates through 166,483 recurrent nodes &bull; Ridge readout trained on held-out split
          </div>
        </div>
      )}
    </form>
  );
};
