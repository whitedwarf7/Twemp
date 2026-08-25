"use client";

import { Bot, BrainCircuit, ChevronRight, Network, RadioTower, Zap } from "lucide-react";
import { useMemo, useState } from "react";

import { cn } from "@/lib/cn";
import type { AgentRuntime, Team, WorkflowRun } from "@/lib/workflow/schemas";
import {
  AgentStatusIcon,
  TEAM_STYLES,
} from "@/components/workflow-primitives";

const teamOrder: Array<Exclude<Team, "command">> = [
  "triage",
  "investigation",
  "response",
  "communications",
];

function statusCopy(status: AgentRuntime["status"]): string {
  return {
    queued: "Queued",
    running: "Running",
    completed: "Complete",
    blocked: "Gated",
    cancelled: "Cancelled",
    failed: "Failed",
  }[status];
}

export function AgentTopology({ run }: { run: WorkflowRun }) {
  const [selectedId, setSelectedId] = useState("incident-commander");
  const selected = run.agents.find((agent) => agent.id === selectedId) ?? run.agents[0];
  const commander = run.agents.find((agent) => agent.role === "main-orchestrator");
  const grouped = useMemo(
    () =>
      teamOrder.map((team) => ({
        team,
        orchestrator: run.agents.find(
          (agent) => agent.team === team && agent.role === "sub-orchestrator",
        ),
        specialists: run.agents.filter(
          (agent) => agent.team === team && agent.role === "specialist",
        ),
      })),
    [run.agents],
  );

  if (!commander) return null;

  return (
    <section className="twemp-panel overflow-hidden">
      <div className="flex items-center justify-between border-b border-white/[0.065] px-4 py-3.5 sm:px-5">
        <div className="flex items-center gap-2.5">
          <div className="grid size-7 place-items-center rounded-lg border border-emerald-300/15 bg-emerald-300/[0.06] text-emerald-300">
            <Network className="size-3.5" />
          </div>
          <div>
            <h2 className="text-xs font-semibold text-white/85">Agent topology</h2>
            <p className="mt-0.5 text-[9px] uppercase tracking-[0.13em] text-white/27">
              Hierarchical execution graph
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 rounded-full border border-white/[0.07] bg-white/[0.025] px-2.5 py-1">
          <RadioTower className="size-3 text-emerald-300" />
          <span className="font-mono text-[9px] uppercase tracking-[0.12em] text-white/38">
            {run.agents.filter((agent) => agent.status === "completed").length} nodes settled
          </span>
        </div>
      </div>

      <div className="relative px-3 py-5 sm:px-5">
        <button
          type="button"
          onClick={() => setSelectedId(commander.id)}
          className={cn(
            "relative z-10 mx-auto flex w-full max-w-[330px] items-center gap-3 rounded-xl border p-3 text-left transition",
            selectedId === commander.id
              ? "border-emerald-300/30 bg-emerald-300/[0.09] shadow-[0_0_35px_rgba(110,231,183,0.05)]"
              : "border-emerald-300/15 bg-emerald-300/[0.045] hover:border-emerald-300/25",
          )}
        >
          <div className="grid size-9 place-items-center rounded-lg border border-emerald-300/15 bg-emerald-300/10 text-emerald-200">
            <BrainCircuit className="size-[17px]" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-white">{commander.name}</span>
              <span className="rounded bg-emerald-300/10 px-1.5 py-0.5 font-mono text-[7px] uppercase tracking-wider text-emerald-200/70">
                Main
              </span>
            </div>
            <p className="mt-1 truncate text-[9px] text-white/36">
              {commander.currentTask ?? commander.outputSummary ?? commander.mission}
            </p>
          </div>
          <div className="flex items-center gap-1.5 text-[9px] text-white/38">
            <AgentStatusIcon status={commander.status} />
            {statusCopy(commander.status)}
          </div>
        </button>

        <div className="mx-auto h-6 w-px bg-gradient-to-b from-emerald-300/40 to-white/10" />
        <div className="absolute left-[12.5%] right-[12.5%] top-[139px] hidden h-px bg-white/[0.09] xl:block" />

        <div className="grid gap-2.5 sm:grid-cols-2 xl:grid-cols-4">
          {grouped.map(({ team, orchestrator, specialists }) => {
            if (!orchestrator) return null;
            const style = TEAM_STYLES[team];
            const complete = specialists.filter((agent) => agent.status === "completed").length;
            return (
              <div
                key={team}
                className={cn(
                  "relative rounded-xl border bg-black/10 p-2.5",
                  style.border,
                )}
              >
                <span className="absolute left-1/2 top-0 hidden h-3 w-px -translate-y-full bg-white/[0.09] xl:block" />
                <button
                  type="button"
                  onClick={() => setSelectedId(orchestrator.id)}
                  className={cn(
                    "flex w-full items-center gap-2 rounded-lg border p-2.5 text-left transition",
                    selectedId === orchestrator.id
                      ? cn(style.border, style.bg)
                      : "border-white/[0.055] bg-white/[0.02] hover:bg-white/[0.04]",
                  )}
                >
                  <div className={cn("grid size-7 place-items-center rounded-md", style.bg, style.accent)}>
                    <Zap className="size-3.5" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-[10px] font-semibold text-white/76">
                      {orchestrator.shortName}
                    </p>
                    <p className="mt-0.5 font-mono text-[8px] text-white/28">
                      {complete}/{specialists.length} agents
                    </p>
                  </div>
                  <AgentStatusIcon status={orchestrator.status} />
                </button>

                <div className="my-1.5 ml-6 h-2 w-px bg-white/[0.07]" />
                <div className="space-y-1.5">
                  {specialists.map((agent) => (
                    <button
                      key={agent.id}
                      type="button"
                      onClick={() => setSelectedId(agent.id)}
                      className={cn(
                        "group flex w-full items-center gap-2 rounded-lg border px-2 py-2 text-left transition",
                        selectedId === agent.id
                          ? cn(style.border, style.bg)
                          : "border-white/[0.045] bg-white/[0.015] hover:border-white/[0.09] hover:bg-white/[0.03]",
                      )}
                    >
                      <Bot className={cn("size-3 shrink-0", style.accent, "opacity-60")} />
                      <span className="min-w-0 flex-1 truncate text-[9px] text-white/52 group-hover:text-white/70">
                        {agent.shortName}
                      </span>
                      <AgentStatusIcon status={agent.status} />
                    </button>
                  ))}
                </div>
              </div>
            );
          })}
        </div>

        {selected && (
          <div className="mt-3 flex flex-col gap-3 rounded-xl border border-white/[0.065] bg-white/[0.018] p-3 sm:flex-row sm:items-center">
            <div className={cn("size-1.5 shrink-0 rounded-full", TEAM_STYLES[selected.team].dot)} />
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-[10px] font-semibold text-white/70">{selected.name}</p>
                <span className="font-mono text-[8px] uppercase tracking-[0.12em] text-white/24">
                  {selected.role.replace("-", " ")}
                </span>
              </div>
              <p className="mt-1 truncate text-[9px] text-white/32">
                {selected.outputSummary ?? selected.currentTask ?? selected.mission}
              </p>
            </div>
            <div className="flex shrink-0 items-center gap-1.5">
              {selected.capabilities.slice(0, 2).map((capability) => (
                <span
                  key={capability}
                  className="rounded-md border border-white/[0.06] bg-black/10 px-2 py-1 text-[8px] text-white/28"
                >
                  {capability}
                </span>
              ))}
              <ChevronRight className="size-3 text-white/20" />
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
