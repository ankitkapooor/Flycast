"use client";

import React, { useState } from "react";
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
} from "recharts";
import { ChartPoint } from "../lib/types";

interface ForecastChartProps {
  historyPoints: ChartPoint[];
  testPoints: ChartPoint[];
  futurePoints: ChartPoint[];
  targetName: string;
}

export const ForecastChart: React.FC<ForecastChartProps> = ({
  historyPoints,
  testPoints,
  futurePoints,
  targetName,
}) => {
  // Model visibility toggles
  const [showPersistence, setShowPersistence] = useState<boolean>(true);
  const [showAR, setShowAR] = useState<boolean>(true);
  const [showInterval, setShowInterval] = useState<boolean>(true);

  // Combine points sequentially into a continuous chart series
  // For smooth connection, bridge segments:
  const combinedData: any[] = [];

  // History
  historyPoints.forEach((p) => {
    combinedData.push({
      time: p.time,
      step: p.step,
      actual: p.actual,
      segment: "history",
    });
  });

  // Test
  testPoints.forEach((p) => {
    combinedData.push({
      time: p.time,
      step: p.step,
      actual: p.actual,
      flycast: p.flycast,
      persistence: p.persistence,
      autoregressive: p.autoregressive,
      segment: "test",
    });
  });

  // Future
  futurePoints.forEach((p) => {
    combinedData.push({
      time: p.time,
      step: p.step,
      flycast: p.flycast,
      persistence: p.persistence,
      autoregressive: p.autoregressive,
      lower_95: p.lower_95,
      upper_95: p.upper_95,
      // Range for area shading: [lower, upper]
      interval_range: [p.lower_95, p.upper_95],
      segment: "future",
    });
  });

  const testStartIndex = historyPoints.length;
  const futureStartIndex = historyPoints.length + testPoints.length;

  const testSplitTime = combinedData[testStartIndex]?.time;
  const futureSplitTime = combinedData[futureStartIndex]?.time;

  return (
    <div className="space-y-4 font-mono">
      {/* Chart Controls & Legend Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-paper-border pb-3 text-xs">
        <div className="flex items-center gap-4">
          <span className="font-bold uppercase text-foreground">
            CHART / {targetName.toUpperCase()}
          </span>
          <div className="flex items-center gap-1.5 text-[11px] text-foreground/60">
            <span className="h-2 w-2 rounded-full bg-black" />
            <span>Actual</span>
          </div>
          <div className="flex items-center gap-1.5 text-[11px] text-fly font-bold">
            <span className="h-2 w-2 rounded-full bg-fly" />
            <span>FlyCast (MaleCNS)</span>
          </div>
        </div>

        {/* Toggle checkboxes */}
        <div className="flex items-center gap-4 text-[11px]">
          <label className="flex items-center gap-1.5 cursor-pointer text-obs-autoregressive font-medium">
            <input
              type="checkbox"
              checked={showAR}
              onChange={(e) => setShowAR(e.target.checked)}
              className="accent-obs-autoregressive h-3.5 w-3.5"
            />
            <span>Autoregressive</span>
          </label>
          <label className="flex items-center gap-1.5 cursor-pointer text-obs-persistence">
            <input
              type="checkbox"
              checked={showPersistence}
              onChange={(e) => setShowPersistence(e.target.checked)}
              className="accent-obs-persistence h-3.5 w-3.5"
            />
            <span>Persistence</span>
          </label>
          <label className="flex items-center gap-1.5 cursor-pointer text-foreground/60">
            <input
              type="checkbox"
              checked={showInterval}
              onChange={(e) => setShowInterval(e.target.checked)}
              className="accent-fly h-3.5 w-3.5"
            />
            <span>Residual Interval</span>
          </label>
        </div>
      </div>

      {/* Recharts Canvas */}
      <div className="h-80 sm:h-96 w-full border border-paper-border bg-paper-light p-2 rounded-sm">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={combinedData} margin={{ top: 15, right: 20, bottom: 20, left: 10 }}>
            <CartesianGrid strokeDasharray="2 2" stroke="#E2DCD0" />
            <XAxis
              dataKey="time"
              tick={{ fontSize: 10, fill: "#7A7870", fontFamily: "ui-monospace" }}
              tickLine={{ stroke: "#C4BFB3" }}
              interval="preserveStartEnd"
              minTickGap={40}
            />
            <YAxis
              domain={["auto", "auto"]}
              tick={{ fontSize: 10, fill: "#7A7870", fontFamily: "ui-monospace" }}
              tickLine={{ stroke: "#C4BFB3" }}
              width={45}
            />
            <Tooltip
              content={({ active, payload, label }) => {
                if (!active || !payload || payload.length === 0) return null;
                const pt = payload[0]?.payload;
                return (
                  <div className="border border-paper-border bg-paper p-3 rounded shadow-md text-xs font-mono space-y-1.5">
                    <div className="flex items-center justify-between gap-4 font-bold border-b border-paper-border pb-1">
                      <span>{label}</span>
                      <span className="text-[10px] uppercase text-foreground/50">{pt?.segment}</span>
                    </div>
                    {pt?.actual !== undefined && pt?.actual !== null && (
                      <div className="flex items-center justify-between gap-4 text-foreground">
                        <span>Actual:</span>
                        <span className="font-bold">{pt.actual.toFixed(4)}</span>
                      </div>
                    )}
                    {pt?.flycast !== undefined && pt?.flycast !== null && (
                      <div className="flex items-center justify-between gap-4 text-fly font-bold">
                        <span>FlyCast:</span>
                        <span>{pt.flycast.toFixed(4)}</span>
                      </div>
                    )}
                    {pt?.autoregressive !== undefined && pt?.autoregressive !== null && showAR && (
                      <div className="flex items-center justify-between gap-4 text-obs-autoregressive">
                        <span>Autoregressive:</span>
                        <span>{pt.autoregressive.toFixed(4)}</span>
                      </div>
                    )}
                    {pt?.persistence !== undefined && pt?.persistence !== null && showPersistence && (
                      <div className="flex items-center justify-between gap-4 text-obs-persistence">
                        <span>Persistence:</span>
                        <span>{pt.persistence.toFixed(4)}</span>
                      </div>
                    )}
                    {pt?.segment === "future" && pt?.lower_95 !== undefined && showInterval && (
                      <div className="text-[10px] text-foreground/60 pt-1 border-t border-paper-border">
                        Interval: [{pt.lower_95.toFixed(3)}, {pt.upper_95.toFixed(3)}]
                      </div>
                    )}
                  </div>
                );
              }}
            />

            {/* Segment boundary vertical markers */}
            {testSplitTime && (
              <ReferenceLine
                x={testSplitTime}
                stroke="#A8A397"
                strokeDasharray="3 3"
                label={{ value: "TEST SET", fill: "#7A7870", fontSize: 9, position: "insideTopLeft" }}
              />
            )}
            {futureSplitTime && (
              <ReferenceLine
                x={futureSplitTime}
                stroke="#C2410C"
                strokeDasharray="3 3"
                label={{ value: "FUTURE", fill: "#C2410C", fontSize: 9, position: "insideTopLeft" }}
              />
            )}

            {/* Approximate residual interval bounds for future forecast */}
            {showInterval && (
              <Area
                type="monotone"
                dataKey="interval_range"
                fill="#C2410C"
                fillOpacity={0.15}
                stroke="#FDBA74"
                strokeWidth={1}
                strokeDasharray="2 2"
                isAnimationActive={false}
              />
            )}

            {/* Actual series */}
            <Line
              type="monotone"
              dataKey="actual"
              stroke="#1A1A18"
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />

            {/* FlyCast prediction */}
            <Line
              type="monotone"
              dataKey="flycast"
              stroke="#C2410C"
              strokeWidth={2.5}
              dot={{ r: 2.5, fill: "#C2410C" }}
              isAnimationActive={false}
            />

            {/* Autoregressive Ridge */}
            {showAR && (
              <Line
                type="monotone"
                dataKey="autoregressive"
                stroke="#0D9488"
                strokeWidth={1.5}
                strokeDasharray="4 2"
                dot={false}
                isAnimationActive={false}
              />
            )}

            {/* Persistence */}
            {showPersistence && (
              <Line
                type="monotone"
                dataKey="persistence"
                stroke="#64748B"
                strokeWidth={1.5}
                strokeDasharray="2 2"
                dot={false}
                isAnimationActive={false}
              />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <div className="flex flex-wrap items-center justify-between text-[11px] text-foreground/60 px-1">
        <span>History &rarr; Held-out Test &rarr; Multi-horizon Future</span>
        <span>Interval: Approximate &plusmn;1.96 &sigma; validation residual</span>
      </div>
    </div>
  );
};
