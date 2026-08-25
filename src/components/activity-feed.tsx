"use client";

import {
  Activity,
  CheckCircle2,
  Clock3,
  FileSearch,
  GitMerge,
  MessageSquareText,
  Play,
  ShieldCheck,
  Siren,
} from "lucide-react";
import { useMemo, useState } from "react";

import { cn } from "@/lib/cn";
import type { WorkflowEvent, WorkflowRun } from "@/lib/workflow/schemas";
import { PhaseLabel, TEAM_STYLES } from "@/components/workflow-primitives";

type FeedFilter = "all" | "evidence" | "actions";

const filterTypes: Record<Exclude<FeedFilter, "all">, WorkflowEvent["type"][]> = {
  evidence: ["finding", "synthesis", "plan-ready"],
  actions: [
    "approval-requested",
    "approval-granted",
    "approval-rejected",
    "remediation",
    "verification",
    "workflow-completed",
    "workflow-failed",
  ],
};

function EventIcon({ type }: { type: WorkflowEvent["type"] }) {
  const className = "size-3.5";
  if (type === "finding") return <FileSearch className={className} />;
  if (type === "synthesis" || type === "delegation") return <GitMerge className={className} />;
  if (type === "communication") return <MessageSquareText className={className} />;
  if (type.includes("approval")) return <ShieldCheck className={className} />;
  if (type === "remediation") return <Play className={className} />;
  if (type === "workflow-completed" || type === "verification") {
    return <CheckCircle2 className={className} />;
  }
  if (type === "workflow-failed") return <Siren className={className} />;
  return <Activity className={className} />;
}

const levelStyles: Record<WorkflowEvent["level"], string> = {
  neutral: "border-white/[0.08] bg-white/[0.025] text-white/42",
  success: "border-emerald-300/18 bg-emerald-300/[0.055] text-emerald-200/75",
  warning: "border-amber-300/18 bg-amber-300/[0.055] text-amber-200/75",
  critical: "border-rose-300/18 bg-rose-300/[0.055] text-rose-200/75",
};

export function ActivityFeed({ run }: { run: WorkflowRun }) {
  const [filter, setFilter] = useState<FeedFilter>("all");
  const events = useMemo(() => {
    const candidates =
      filter === "all"
        ? run.events
        : run.events.filter((event) => filterTypes[filter].includes(event.type));
    return [...candidates].reverse();
  }, [filter, run.events]);

  return (
    <section className="twemp-panel overflow-hidden">
      <div className="flex flex-wrap items-center gap-3 border-b border-white/[0.065] px-4 py-3.5 sm:px-5">
        <div className="flex items-center gap-2.5">
          <div className="grid size-7 place-items-center rounded-lg border border-cyan-300/15 bg-cyan-300/[0.06] text-cyan-300">
            <Activity className="size-3.5" />
          </div>
          <div>
            <h2 className="text-xs font-semibold text-white/85">Command stream</h2>
            <p className="mt-0.5 text-[9px] uppercase tracking-[0.13em] text-white/27">
              Ordered event ledger
            </p>
          </div>
        </div>

        <div className="ml-auto flex rounded-lg border border-white/[0.065] bg-black/10 p-0.5">
          {(["all", "evidence", "actions"] as FeedFilter[]).map((option) => (
            <button
              key={option}
              type="button"
              onClick={() => setFilter(option)}
              className={cn(
                "rounded-md px-2.5 py-1 text-[9px] capitalize transition",
                filter === option
                  ? "bg-white/[0.08] text-white/70"
                  : "text-white/28 hover:text-white/50",
              )}
            >
              {option}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-1.5 font-mono text-[9px] text-white/28">
          <span className="relative flex size-1.5">
            <span className="absolute inline-flex size-full animate-ping rounded-full bg-emerald-300 opacity-50" />
            <span className="relative inline-flex size-1.5 rounded-full bg-emerald-300" />
          </span>
          {events.length} events
        </div>
      </div>

      <div className="twemp-scrollbar max-h-[490px] overflow-y-auto px-3 py-2 sm:px-4">
        {events.map((event, index) => {
          const teamStyle = TEAM_STYLES[event.team];
          return (
            <article
              key={event.id}
              className="twemp-event-enter group relative grid grid-cols-[32px_minmax(0,1fr)] gap-2.5 py-2.5"
              style={{ animationDelay: `${Math.min(index * 25, 250)}ms` }}
            >
              {index < events.length - 1 && (
                <span className="absolute bottom-[-10px] left-[15px] top-[39px] w-px bg-white/[0.055]" />
              )}
              <div
                className={cn(
                  "relative z-10 grid size-8 place-items-center rounded-lg border",
                  levelStyles[event.level],
                )}
              >
                <EventIcon type={event.type} />
              </div>
              <div className="min-w-0 rounded-xl border border-transparent px-1.5 py-0.5 transition group-hover:border-white/[0.045] group-hover:bg-white/[0.015]">
                <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
                  <p className="min-w-0 truncate text-[11px] font-medium text-white/70">
                    {event.title}
                  </p>
                  <PhaseLabel phase={event.phase} />
                  <span className="ml-auto flex items-center gap-1 font-mono text-[8px] tabular-nums text-white/23">
                    <Clock3 className="size-2.5" />
                    {new Date(event.timestamp).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                      second: "2-digit",
                    })}
                  </span>
                </div>
                <p className="mt-1 line-clamp-2 text-[10px] leading-[1.55] text-white/32">
                  {event.detail}
                </p>
                <div className="mt-1.5 flex items-center gap-1.5">
                  <span className={cn("size-1 rounded-full", teamStyle.dot)} />
                  <span className={cn("text-[8px] font-medium", teamStyle.accent)}>
                    {event.actorName}
                  </span>
                  <span className="font-mono text-[7px] text-white/17">#{event.sequence}</span>
                </div>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
