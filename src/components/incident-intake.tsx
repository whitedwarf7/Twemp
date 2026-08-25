"use client";

import {
  ArrowRight,
  Bot,
  BrainCircuit,
  Check,
  Network,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

import { cn } from "@/lib/cn";
import type { IncidentInput, Severity } from "@/lib/workflow/schemas";

interface IncidentIntakeProps {
  draft: IncidentInput;
  isStarting: boolean;
  error: string | null;
  onChange: (patch: Partial<IncidentInput>) => void;
  onStart: () => void;
}

const teams = [
  { name: "Triage", count: 3, color: "bg-amber-300", border: "border-amber-300/15" },
  { name: "Investigation", count: 3, color: "bg-cyan-300", border: "border-cyan-300/15" },
  { name: "Response", count: 3, color: "bg-violet-300", border: "border-violet-300/15" },
  { name: "Communications", count: 3, color: "bg-rose-300", border: "border-rose-300/15" },
];

const severityOptions: Severity[] = ["SEV-1", "SEV-2", "SEV-3"];

export function IncidentIntake({
  draft,
  isStarting,
  error,
  onChange,
  onStart,
}: IncidentIntakeProps) {
  return (
    <main className="relative isolate mx-auto w-full max-w-[1680px] flex-1 overflow-hidden px-4 pb-12 pt-10 sm:px-6 lg:px-8 lg:pt-16">
      <div className="pointer-events-none absolute left-[8%] top-0 -z-10 size-[520px] rounded-full bg-emerald-400/[0.055] blur-[120px]" />
      <div className="pointer-events-none absolute right-[4%] top-[22%] -z-10 size-[420px] rounded-full bg-cyan-400/[0.04] blur-[120px]" />

      <div className="grid items-start gap-10 lg:grid-cols-[1.08fr_0.92fr] xl:gap-20">
        <section className="pt-3 lg:pt-8">
          <div className="mb-7 inline-flex items-center gap-2 rounded-full border border-emerald-300/15 bg-emerald-300/[0.06] px-3 py-1.5">
            <Sparkles className="size-3 text-emerald-300" />
            <span className="text-[10px] font-semibold uppercase tracking-[0.18em] text-emerald-200/80">
              Hierarchical agent operations
            </span>
          </div>
          <h1 className="max-w-3xl text-balance text-4xl font-medium leading-[1.03] tracking-[-0.045em] text-white sm:text-6xl xl:text-[72px]">
            One command.
            <br />
            <span className="bg-gradient-to-r from-emerald-200 via-cyan-200 to-white bg-clip-text text-transparent">
              Seventeen agents.
            </span>
          </h1>
          <p className="mt-7 max-w-2xl text-pretty text-base leading-7 text-white/48 sm:text-lg sm:leading-8">
            An approval-gated incident response system where a main commander delegates to
            specialized teams, fuses their evidence, and keeps every remediation behind a human
            decision.
          </p>

          <div className="relative mt-12 max-w-3xl rounded-2xl border border-white/[0.08] bg-white/[0.025] p-4 shadow-2xl shadow-black/20 sm:p-6">
            <div className="absolute inset-0 -z-10 rounded-2xl bg-[radial-gradient(circle_at_50%_0%,rgba(110,231,183,0.05),transparent_48%)]" />
            <div className="mx-auto flex max-w-xs items-center gap-3 rounded-xl border border-emerald-300/20 bg-emerald-300/[0.07] p-3 shadow-[0_0_35px_rgba(110,231,183,0.04)]">
              <div className="grid size-9 place-items-center rounded-lg bg-emerald-300/10 text-emerald-200">
                <BrainCircuit className="size-[18px]" />
              </div>
              <div>
                <p className="text-xs font-semibold text-white">Incident Commander</p>
                <p className="mt-0.5 text-[10px] text-white/38">Global state + policy control</p>
              </div>
              <span className="ml-auto size-2 rounded-full bg-emerald-300 shadow-[0_0_12px_rgba(110,231,183,0.65)]" />
            </div>

            <div className="mx-auto h-7 w-px bg-gradient-to-b from-emerald-300/50 to-white/10" />
            <div className="relative grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
              <div className="absolute left-[12.5%] right-[12.5%] top-0 hidden h-px bg-white/10 xl:block" />
              {teams.map((team) => (
                <div
                  key={team.name}
                  className={cn(
                    "relative rounded-xl border bg-black/10 p-3 pt-4",
                    team.border,
                  )}
                >
                  <span className={cn("absolute left-1/2 top-0 h-3 w-px -translate-y-full bg-white/10", "hidden xl:block")} />
                  <div className="flex items-center gap-2">
                    <Network className="size-3.5 text-white/35" />
                    <span className="truncate text-[11px] font-medium text-white/70">{team.name}</span>
                  </div>
                  <div className="mt-3 flex gap-1.5">
                    {Array.from({ length: team.count }).map((_, index) => (
                      <span
                        // The index is stable because these represent fixed specialist slots.
                        key={index}
                        className="flex size-7 items-center justify-center rounded-md border border-white/[0.06] bg-white/[0.025]"
                      >
                        <Bot className="size-3 text-white/25" />
                        <span className={cn("absolute mt-5 size-1 rounded-full", team.color)} />
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-6 grid gap-3 sm:grid-cols-3">
            {[
              [ShieldCheck, "Human gated", "No remediation before approval"],
              [Network, "Code orchestrated", "Predictable parallel execution"],
              [Check, "Schema checked", "Validated at every boundary"],
            ].map(([Icon, title, copy]) => {
              const FeatureIcon = Icon as typeof ShieldCheck;
              return (
                <div key={title as string} className="flex items-start gap-3 py-2">
                  <FeatureIcon className="mt-0.5 size-4 text-emerald-300/70" />
                  <div>
                    <p className="text-xs font-medium text-white/70">{title as string}</p>
                    <p className="mt-1 text-[11px] leading-4 text-white/32">{copy as string}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        <section className="rounded-2xl border border-white/[0.09] bg-[#0b1513]/90 p-1 shadow-[0_30px_100px_rgba(0,0,0,0.35)]">
          <div className="rounded-[14px] border border-white/[0.04] bg-[linear-gradient(145deg,rgba(255,255,255,0.025),transparent_45%)] p-5 sm:p-7">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-emerald-300/65">
                  New incident
                </p>
                <h2 className="mt-2 text-xl font-medium tracking-tight text-white">
                  Activate response workflow
                </h2>
                <p className="mt-1.5 text-xs leading-5 text-white/38">
                  Starts in deterministic demo mode by default.
                </p>
              </div>
              <div className="rounded-lg border border-white/[0.08] bg-white/[0.035] px-2.5 py-1.5 font-mono text-[9px] uppercase tracking-[0.14em] text-white/40">
                17 agents
              </div>
            </div>

            <div className="mt-7 space-y-5">
              <div>
                <label className="mb-2 block text-[10px] font-medium uppercase tracking-[0.14em] text-white/40">
                  Severity
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {severityOptions.map((severity) => (
                    <button
                      key={severity}
                      type="button"
                      onClick={() => onChange({ severity })}
                      className={cn(
                        "rounded-lg border px-3 py-2 text-[11px] font-semibold transition",
                        draft.severity === severity
                          ? severity === "SEV-1"
                            ? "border-rose-400/35 bg-rose-400/10 text-rose-200"
                            : "border-amber-400/35 bg-amber-400/10 text-amber-200"
                          : "border-white/[0.07] bg-white/[0.025] text-white/35 hover:border-white/15 hover:text-white/60",
                      )}
                    >
                      {severity}
                    </button>
                  ))}
                </div>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <label className="block">
                  <span className="mb-2 block text-[10px] font-medium uppercase tracking-[0.14em] text-white/40">
                    Service
                  </span>
                  <input
                    value={draft.service}
                    onChange={(event) => onChange({ service: event.target.value })}
                    className="twemp-input"
                    placeholder="payment-router"
                  />
                </label>
                <label className="block">
                  <span className="mb-2 block text-[10px] font-medium uppercase tracking-[0.14em] text-white/40">
                    Region
                  </span>
                  <input
                    value={draft.region}
                    onChange={(event) => onChange({ region: event.target.value })}
                    className="twemp-input"
                    placeholder="eu-central"
                  />
                </label>
              </div>

              <label className="block">
                <span className="mb-2 block text-[10px] font-medium uppercase tracking-[0.14em] text-white/40">
                  Incident title
                </span>
                <input
                  value={draft.title}
                  onChange={(event) => onChange({ title: event.target.value })}
                  className="twemp-input"
                />
              </label>

              <label className="block">
                <span className="mb-2 block text-[10px] font-medium uppercase tracking-[0.14em] text-white/40">
                  Observed behavior
                </span>
                <textarea
                  value={draft.description}
                  onChange={(event) => onChange({ description: event.target.value })}
                  className="twemp-input min-h-28 resize-none leading-5"
                />
              </label>

              <div>
                <span className="mb-2 block text-[10px] font-medium uppercase tracking-[0.14em] text-white/40">
                  Seed signals
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {draft.signals.map((signal) => (
                    <span
                      key={signal}
                      className="rounded-md border border-white/[0.07] bg-white/[0.025] px-2 py-1 text-[10px] text-white/40"
                    >
                      {signal}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            {error && (
              <div className="mt-5 rounded-lg border border-rose-400/20 bg-rose-400/[0.07] px-3 py-2.5 text-xs text-rose-200/80">
                {error}
              </div>
            )}

            <button
              type="button"
              disabled={isStarting}
              onClick={onStart}
              className="group mt-7 flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-emerald-300 px-4 text-xs font-semibold text-[#07100e] shadow-[0_10px_30px_rgba(110,231,183,0.12)] transition hover:bg-emerald-200 disabled:cursor-wait disabled:opacity-70"
            >
              {isStarting ? (
                <>
                  <span className="size-3.5 animate-spin rounded-full border-2 border-[#07100e]/25 border-t-[#07100e]" />
                  Delegating workstreams…
                </>
              ) : (
                <>
                  Activate 17-agent response
                  <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" />
                </>
              )}
            </button>
            <div className="mt-3 flex items-center justify-center gap-2 text-center text-[10px] text-white/25">
              <ShieldCheck className="size-3" />
              Workflow pauses before all remediation actions
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
