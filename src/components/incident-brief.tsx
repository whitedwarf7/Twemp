import { ChevronDown, CircleDot, FileText, Gauge, Radar } from "lucide-react";

import { cn } from "@/lib/cn";
import type { WorkflowRun } from "@/lib/workflow/schemas";
import { TEAM_STYLES } from "@/components/workflow-primitives";

export function IncidentBrief({ run }: { run: WorkflowRun }) {
  return (
    <section className="twemp-panel overflow-hidden">
      <div className="flex items-center border-b border-white/[0.065] px-4 py-3.5 sm:px-5">
        <div className="grid size-7 place-items-center rounded-lg border border-white/[0.08] bg-white/[0.03] text-white/45">
          <FileText className="size-3.5" />
        </div>
        <div className="ml-2.5">
          <h2 className="text-xs font-semibold text-white/85">Incident intelligence</h2>
          <p className="mt-0.5 text-[9px] uppercase tracking-[0.13em] text-white/27">
            Evidence + team synthesis
          </p>
        </div>
        <span className="ml-auto font-mono text-[9px] text-white/25">
          {run.findings.length} findings
        </span>
      </div>

      <div className="px-4 py-4 sm:px-5">
        <div>
          <div className="flex items-center gap-2">
            <Radar className="size-3.5 text-rose-300/65" />
            <p className="text-[9px] uppercase tracking-[0.13em] text-white/30">Observed signals</p>
          </div>
          <div className="mt-2.5 space-y-1.5">
            {run.incident.signals.map((signal) => (
              <div
                key={signal}
                className="flex items-center gap-2 rounded-lg border border-white/[0.055] bg-white/[0.018] px-2.5 py-2"
              >
                <CircleDot className="size-3 shrink-0 text-rose-300/55" />
                <span className="text-[9px] text-white/39">{signal}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="my-4 h-px bg-white/[0.06]" />

        <div className="flex items-center justify-between">
          <p className="text-[9px] uppercase tracking-[0.13em] text-white/30">Team reports</p>
          <div className="flex items-center gap-1.5 text-[8px] text-white/23">
            <Gauge className="size-3" /> confidence scored
          </div>
        </div>
        <div className="mt-2.5 space-y-2">
          {run.teamReports.map((report, index) => {
            const style = TEAM_STYLES[report.team];
            return (
              <details
                key={report.id}
                className={cn(
                  "group rounded-xl border bg-white/[0.015]",
                  style.border,
                )}
                open={index === run.teamReports.length - 1}
              >
                <summary className="flex cursor-pointer list-none items-center gap-2.5 px-3 py-2.5">
                  <span className={cn("size-1.5 shrink-0 rounded-full", style.dot)} />
                  <span className="min-w-0 flex-1 truncate text-[9px] font-medium text-white/53">
                    {style.label}
                  </span>
                  <span className={cn("font-mono text-[8px]", style.accent)}>
                    {Math.round(report.confidence * 100)}%
                  </span>
                  <ChevronDown className="size-3 text-white/23 transition group-open:rotate-180" />
                </summary>
                <div className="border-t border-white/[0.05] px-3 py-3">
                  <p className="text-[10px] font-medium leading-4 text-white/55">{report.title}</p>
                  <p className="mt-2 text-[9px] leading-[1.6] text-white/29">{report.summary}</p>
                  <div className="mt-2.5 rounded-lg border border-white/[0.05] bg-black/10 p-2.5">
                    <p className="text-[8px] uppercase tracking-[0.12em] text-white/22">Recommendation</p>
                    <p className="mt-1 text-[9px] leading-4 text-white/38">{report.recommendation}</p>
                  </div>
                </div>
              </details>
            );
          })}
        </div>
      </div>
    </section>
  );
}
