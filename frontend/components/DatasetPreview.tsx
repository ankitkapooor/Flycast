import React from "react";

interface DatasetPreviewProps {
  headers: string[];
  rows: string[][];
  totalRows: number;
  timeColumn: string;
  targetColumn: string;
}

export const DatasetPreview: React.FC<DatasetPreviewProps> = ({
  headers,
  rows,
  totalRows,
  timeColumn,
  targetColumn,
}) => {
  return (
    <div className="space-y-2 font-mono text-xs">
      <div className="flex items-center justify-between text-foreground/60 text-[11px]">
        <span>PREVIEW ({rows.length} of {totalRows.toLocaleString()} detected rows)</span>
        <span className="text-[10px] uppercase">
          Target: <strong className="text-fly">{targetColumn}</strong> | Time: <strong>{timeColumn}</strong>
        </span>
      </div>

      <div className="overflow-x-auto border border-paper-border bg-paper-light rounded-sm">
        <table className="w-full text-left text-foreground border-collapse">
          <thead>
            <tr className="border-b border-paper-border bg-paper-dark/70 text-[11px] text-foreground/70 uppercase">
              {headers.map((h) => (
                <th
                  key={h}
                  className={`px-3 py-2 font-semibold ${
                    h === targetColumn
                      ? "text-fly bg-fly/5"
                      : h === timeColumn
                      ? "text-foreground font-bold"
                      : ""
                  }`}
                >
                  <div className="flex items-center gap-1">
                    <span>{h}</span>
                    {h === targetColumn && <span className="text-[9px] text-fly">★</span>}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-paper-border/60">
            {rows.map((row, rIdx) => (
              <tr key={rIdx} className="hover:bg-paper-dark/40 transition-colors">
                {row.map((cell, cIdx) => (
                  <td
                    key={cIdx}
                    className={`px-3 py-1.5 whitespace-nowrap text-[11px] ${
                      headers[cIdx] === targetColumn ? "font-bold text-fly" : "text-foreground/80"
                    }`}
                  >
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
