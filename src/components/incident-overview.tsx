import {
  Activity,
  ArrowUpRight,
  Bot,
  GitBranch,
  ListChecks,
  ShieldAlert,
  Sparkles,
} from "lucide-react";

import { cn } from "@/lib/cn";
import type { WorkflowPhase, WorkflowRun } from "@/lib/workflow/schemas";
import { WorkflowStatusPill } from "@/components/workflow-primitives";

const phaseOrder: WorkflowPhase[] = [
  "triage",
  "investigation",
  "planning",
  "approval",
  "remediation",
  "verification",
  "resolved",
];

const phaseNames: Partial<Record<WorkflowPhase, string>> = {
  triage: "Triage",
  investigation: "Investigate",
  planning: "Plan",
  approval: "Approve",
  remediation: "Remediate",
  verification: "Verify",
  resolved: "Resolve",
};

function phaseState(run: WorkflowRun, phase: WorkflowPhase) {
  if (run.phase === "failed" || run.phase === "rejected") {
    return phaseOrder.indexOf(phase) < phaseOrder.indexOf("approval") ? "done" : "idle";
  }
  const current = phaseOrder.indexOf(run.phase);
  const index = phaseOrder.indexOf(phase);
  if (index < current) return "done";
  if (index === current) return "current";
  return "idle";
}

export function IncidentOverview({ run }: { run: WorkflowRun }) {
  const metrics = [
    {
      label: "Agents complete",
      value: `${run.metrics.agentsCompleted}/${run.metrics.agentsTotal}`,
      hint: `${run.metrics.activeAgents} active now`,
      icon: Bot,
      color: "text-emerald-300",
    },
    {
      label: "Tasks resolved",
      value: run.metrics.tasksCompleted.toString().padStart(2, "0"),
      hint: "validated outputs",
      icon: ListChecks,
      color: "text-cyan-300",
    },
    {
      label: "Delegations",
      value: run.metrics.handoffs.toString().padStart(2, "0"),
      hint: "across 4 teams",
      icon: GitBranch,
      color: "text-violet-300",
    },
    {
      label: "Confidence",
      value: `${Math.round(run.metrics.confidence * 100)}%`,
      hint: "evidence weighted",
      icon: Sparkles,
      color: "text-amber-300",
    },
  ];

  return (
    <>
      <section className="relative overflow-hidden rounded-2xl border border-white/[0.08] bg-[linear-gradient(130deg,rgba(255,255,255,0.035),rgba(255,255,255,0.012))] px-5 py-5 sm:px-6">
        <div className="pointer-events-none absolute right-0 top-0 size-64 -translate-y-1/2 translate-x-1/3 rounded-full bg-rose-400/[0.04] blur-3xl" />
        <div className="relative flex flex-col gap-5 xl:flex-row xl:items-center">
          <div className="flex min-w-0 flex-1 items-start gap-4">
            <div className="mt-0.5 grid size-11 shrink-0 place-items-center rounded-xl border border-rose-400/20 bg-rose-400/[0.08] text-rose-300">
              <ShieldAlert className="size-5" />
            </div>
            <div className="min-w-0">
              <div className="mb-2 flex flex-wrap items-center gap-2.5">
                <span className="rounded-md border border-rose-400/25 bg-rose-400/10 px-2 py-1 font-mono text-[10px] font-semibold tracking-[0.12em] text-rose-200">
                  {run.incident.severity}
                </span>
                <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/30">
                  {run.id}
                </span>
                <WorkflowStatusPill status={run.status} />
              </div>
              <h1 className="truncate text-xl font-medium tracking-tight text-white sm:text-2xl">
                {run.incident.title}
              </h1>
              <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-[11px] text-white/38">
                <span className="inline-flex items-center gap-1.5">
                  <Activity className="size-3" />
                  {run.incident.service}
                </span>
                <span>{run.incident.region}</span>
                <span>Opened {new Date(run.startedAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
              </div>
            </div>
          </div>

          <div className="w-full xl:max-w-[620px]">
            <div className="flex items-center">
              {phaseOrder.map((phase, index) => {
                const state = phaseState(run, phase);
                return (
                  <div key={phase} className="flex min-w-0 flex-1 items-center last:flex-none">
                    <div className="flex min-w-0 flex-col items-center gap-1.5">
                      <span
                        className={cn(
                          "grid size-5 place-items-center rounded-full border text-[8px] font-bold transition",
                          state === "done" && "border-emerald-300/40 bg-emerald-300 text-[#07100e]",
                          state === "current" && "border-amber-300/45 bg-amber-300/15 text-amber-200 shadow-[0_0_20px_rgba(252,211,77,0.12)]",
                          state === "idle" && "border-white/10 bg-white/[0.025] text-white/25",
                        )}
                      >
                        {state === "done" ? "✓" : index + 1}
                      </span>
                      <span
                        className={cn(
                          "hidden whitespace-nowrap font-mono text-[8px] uppercase tracking-[0.1em] sm:block",
                          state === "current" ? "text-amber-200/80" : state === "done" ? "text-emerald-200/55" : "text-white/20",
                        )}
                      >
                        {phaseNames[phase]}
                      </span>
                    </div>
                    {index < phaseOrder.length - 1 && (
                      <span
                        className={cn(
                          "mb-4 h-px min-w-3 flex-1",
                          state === "done" ? "bg-emerald-300/35" : "bg-white/[0.07]",
                        )}
                      />
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </section>

      <section className="mt-3 grid grid-cols-2 gap-3 xl:grid-cols-4">
        {metrics.map((metric) => {
          const Icon = metric.icon;
          return (
            <div
              key={metric.label}
              className="group rounded-xl border border-white/[0.075] bg-white/[0.022] px-4 py-3.5 transition hover:border-white/[0.12] hover:bg-white/[0.035]"
            >
              <div className="flex items-center justify-between">
                <p className="text-[10px] uppercase tracking-[0.13em] text-white/32">{metric.label}</p>
                <Icon className={cn("size-3.5 opacity-65", metric.color)} />
              </div>
              <div className="mt-2 flex items-end gap-2">
                <p className="font-mono text-xl font-medium tracking-tight text-white/90">{metric.value}</p>
                <p className="mb-0.5 text-[9px] text-white/25">{metric.hint}</p>
                <ArrowUpRight className="mb-1 ml-auto size-3 text-white/15 transition group-hover:text-white/35" />
              </div>
            </div>
          );
        })}
      </section>
    </>
  );
}
