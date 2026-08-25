"use client";

import {
  Check,
  CheckCircle2,
  ChevronDown,
  CircleAlert,
  FlaskConical,
  LockKeyhole,
  ShieldCheck,
  TriangleAlert,
  Undo2,
  UserRound,
  X,
  XCircle,
} from "lucide-react";
import { useState } from "react";

import { cn } from "@/lib/cn";
import type { ApprovalDecision, WorkflowRun } from "@/lib/workflow/schemas";

interface DecisionPanelProps {
  run: WorkflowRun;
  isDeciding: boolean;
  error: string | null;
  onDecision: (decision: ApprovalDecision) => void;
}

function PlanSummary({ run }: { run: WorkflowRun }) {
  if (!run.plan) return null;
  return (
    <div className="space-y-3">
      <div className="rounded-xl border border-white/[0.065] bg-black/10 p-3.5">
        <p className="text-[9px] uppercase tracking-[0.14em] text-white/28">Leading hypothesis</p>
        <p className="mt-2 text-[10px] leading-[1.65] text-white/50">{run.plan.hypothesis}</p>
      </div>
      <div className="space-y-2">
        {run.plan.actions.map((action, index) => (
          <div
            key={action.id}
            className="group rounded-xl border border-white/[0.06] bg-white/[0.018] p-3 transition hover:border-white/[0.1]"
          >
            <div className="flex items-start gap-2.5">
              <span className="grid size-5 shrink-0 place-items-center rounded-md border border-violet-300/15 bg-violet-300/[0.07] font-mono text-[8px] text-violet-200">
                {index + 1}
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <p className="text-[10px] font-medium text-white/68">{action.title}</p>
                  <span
                    className={cn(
                      "ml-auto rounded px-1.5 py-0.5 font-mono text-[7px] uppercase",
                      action.risk === "low"
                        ? "bg-emerald-300/10 text-emerald-200/60"
                        : action.risk === "medium"
                          ? "bg-amber-300/10 text-amber-200/60"
                          : "bg-rose-300/10 text-rose-200/60",
                    )}
                  >
                    {action.risk}
                  </span>
                </div>
                <p className="mt-1.5 line-clamp-2 text-[9px] leading-[1.55] text-white/30">
                  {action.detail}
                </p>
                <div className="mt-2 flex items-center gap-1 text-[8px] text-emerald-200/45">
                  <Undo2 className="size-2.5" />
                  {action.reversible ? "Reversible" : "Not reversible"}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
      <details className="group rounded-xl border border-white/[0.06] bg-white/[0.018]">
        <summary className="flex cursor-pointer list-none items-center gap-2 px-3 py-2.5 text-[9px] font-medium text-white/45">
          <Undo2 className="size-3 text-amber-300/60" />
          Rollback criteria
          <ChevronDown className="ml-auto size-3 transition group-open:rotate-180" />
        </summary>
        <p className="border-t border-white/[0.055] px-3 py-2.5 text-[9px] leading-[1.6] text-white/30">
          {run.plan.rollback}
        </p>
      </details>
    </div>
  );
}

function AwaitingApproval({
  run,
  isDeciding,
  error,
  onDecision,
}: DecisionPanelProps) {
  const [reviewer, setReviewer] = useState("On-call lead");
  const [note, setNote] = useState("");
  const [acknowledged, setAcknowledged] = useState(false);

  return (
    <section className="overflow-hidden rounded-2xl border border-amber-300/20 bg-[linear-gradient(145deg,rgba(252,211,77,0.07),rgba(255,255,255,0.018)_35%)] shadow-[0_18px_50px_rgba(0,0,0,0.2)]">
      <div className="border-b border-amber-300/12 px-4 py-4 sm:px-5">
        <div className="flex items-start gap-3">
          <div className="grid size-9 shrink-0 place-items-center rounded-xl border border-amber-300/20 bg-amber-300/10 text-amber-200">
            <LockKeyhole className="size-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <p className="font-mono text-[9px] uppercase tracking-[0.16em] text-amber-200/55">
                Policy gate 01
              </p>
              <span className="relative flex size-1.5">
                <span className="absolute inline-flex size-full animate-ping rounded-full bg-amber-300 opacity-50" />
                <span className="relative size-1.5 rounded-full bg-amber-300" />
              </span>
            </div>
            <h2 className="mt-1.5 text-sm font-semibold text-white/90">Approval required</h2>
            <p className="mt-1 text-[10px] leading-4 text-white/36">
              Agents are paused. No remediation has run.
            </p>
          </div>
          <span className="ml-auto rounded-md border border-amber-300/15 bg-amber-300/[0.07] px-2 py-1 font-mono text-[8px] uppercase tracking-[0.12em] text-amber-200/60">
            {run.plan?.riskLevel} risk
          </span>
        </div>
      </div>

      <div className="twemp-scrollbar max-h-[500px] overflow-y-auto px-4 py-4 sm:px-5">
        <PlanSummary run={run} />

        <div className="mt-4 grid grid-cols-2 gap-2">
          <div className="rounded-lg border border-white/[0.06] bg-black/10 p-2.5">
            <p className="text-[8px] uppercase tracking-[0.12em] text-white/25">Blast radius</p>
            <p className="mt-1 line-clamp-2 text-[9px] leading-4 text-white/42">{run.plan?.blastRadius}</p>
          </div>
          <div className="rounded-lg border border-white/[0.06] bg-black/10 p-2.5">
            <p className="text-[8px] uppercase tracking-[0.12em] text-white/25">Success checks</p>
            <p className="mt-1 text-[9px] leading-4 text-white/42">
              {run.plan?.validationChecks.length} predeclared signals
            </p>
          </div>
        </div>

        <div className="mt-4 space-y-3 border-t border-white/[0.06] pt-4">
          <label className="block">
            <span className="mb-1.5 flex items-center gap-1.5 text-[9px] uppercase tracking-[0.12em] text-white/30">
              <UserRound className="size-3" /> Reviewer
            </span>
            <input
              value={reviewer}
              onChange={(event) => setReviewer(event.target.value)}
              maxLength={80}
              className="twemp-input h-9 py-2 text-[10px]"
            />
          </label>
          <label className="block">
            <span className="mb-1.5 block text-[9px] uppercase tracking-[0.12em] text-white/30">
              Decision note <span className="normal-case tracking-normal text-white/18">(optional)</span>
            </span>
            <textarea
              value={note}
              onChange={(event) => setNote(event.target.value)}
              maxLength={500}
              placeholder="Add constraints or rationale…"
              className="twemp-input min-h-16 resize-none py-2 text-[10px] leading-4"
            />
          </label>
          <label className="flex cursor-pointer items-start gap-2.5 rounded-lg border border-white/[0.06] bg-white/[0.018] p-2.5">
            <input
              type="checkbox"
              checked={acknowledged}
              onChange={(event) => setAcknowledged(event.target.checked)}
              className="mt-0.5 size-3.5 accent-emerald-300"
            />
            <span className="text-[9px] leading-4 text-white/38">
              I reviewed the blast radius, rollback criteria, and validation checks.
            </span>
          </label>
        </div>

        {error && (
          <div className="mt-3 flex items-start gap-2 rounded-lg border border-rose-300/15 bg-rose-300/[0.06] p-2.5 text-[9px] leading-4 text-rose-200/70">
            <CircleAlert className="mt-0.5 size-3 shrink-0" />
            {error}
          </div>
        )}
      </div>

      <div className="border-t border-white/[0.06] bg-black/10 px-4 py-3.5 sm:px-5">
        <div className="grid grid-cols-[0.72fr_1.28fr] gap-2">
          <button
            type="button"
            disabled={isDeciding || reviewer.trim().length < 2}
            onClick={() => onDecision({ decision: "reject", reviewer, note })}
            className="flex h-10 items-center justify-center gap-1.5 rounded-lg border border-rose-300/15 bg-rose-300/[0.045] text-[10px] font-medium text-rose-200/65 transition hover:border-rose-300/25 hover:bg-rose-300/[0.08] disabled:opacity-40"
          >
            <X className="size-3.5" /> Reject
          </button>
          <button
            type="button"
            disabled={isDeciding || !acknowledged || reviewer.trim().length < 2}
            onClick={() => onDecision({ decision: "approve", reviewer, note })}
            className="flex h-10 items-center justify-center gap-1.5 rounded-lg bg-emerald-300 text-[10px] font-semibold text-[#07100e] transition hover:bg-emerald-200 disabled:cursor-not-allowed disabled:opacity-35"
          >
            {isDeciding ? (
              <span className="size-3.5 animate-spin rounded-full border-2 border-[#07100e]/25 border-t-[#07100e]" />
            ) : (
              <ShieldCheck className="size-3.5" />
            )}
            Approve simulation
          </button>
        </div>
        <p className="mt-2 flex items-center justify-center gap-1.5 text-[8px] text-white/20">
          <FlaskConical className="size-2.5" /> Reference adapter records simulated actions only
        </p>
      </div>
    </section>
  );
}

function ResolvedPanel({ run }: { run: WorkflowRun }) {
  return (
    <section className="overflow-hidden rounded-2xl border border-emerald-300/20 bg-[linear-gradient(145deg,rgba(110,231,183,0.075),rgba(255,255,255,0.018)_38%)]">
      <div className="border-b border-emerald-300/12 px-5 py-4">
        <div className="flex items-center gap-3">
          <div className="grid size-9 place-items-center rounded-xl border border-emerald-300/20 bg-emerald-300/10 text-emerald-200">
            <CheckCircle2 className="size-4.5" />
          </div>
          <div>
            <p className="font-mono text-[9px] uppercase tracking-[0.16em] text-emerald-200/55">
              Command resolved
            </p>
            <h2 className="mt-1 text-sm font-semibold text-white/90">Recovery verified</h2>
          </div>
          <span className="ml-auto rounded-full border border-emerald-300/15 bg-emerald-300/[0.07] px-2.5 py-1 text-[8px] font-medium text-emerald-200/60">
            {run.approval?.decidedBy}
          </span>
        </div>
      </div>
      <div className="space-y-4 px-5 py-4">
        <div>
          <p className="text-[9px] uppercase tracking-[0.13em] text-white/27">Root cause</p>
          <p className="mt-2 text-[10px] leading-[1.65] text-white/50">{run.outcome?.rootCause}</p>
        </div>
        <div className="grid grid-cols-2 gap-2">
          {run.verification?.checks.map((check) => (
            <div key={check.label} className="rounded-xl border border-white/[0.06] bg-black/10 p-3">
              <div className="flex items-center gap-1.5 text-emerald-200/65">
                <Check className="size-3" />
                <span className="font-mono text-[10px] font-medium">{check.value}</span>
              </div>
              <p className="mt-1.5 text-[8px] leading-3 text-white/30">{check.label}</p>
            </div>
          ))}
        </div>
        <details className="group rounded-xl border border-white/[0.06] bg-white/[0.018]" open>
          <summary className="flex cursor-pointer list-none items-center px-3 py-2.5 text-[9px] font-medium text-white/45">
            Prevention work
            <ChevronDown className="ml-auto size-3 transition group-open:rotate-180" />
          </summary>
          <ul className="space-y-2 border-t border-white/[0.055] px-3 py-3">
            {run.outcome?.followUps.map((followUp) => (
              <li key={followUp} className="flex gap-2 text-[9px] leading-4 text-white/34">
                <span className="mt-1.5 size-1 shrink-0 rounded-full bg-emerald-300/60" />
                {followUp}
              </li>
            ))}
          </ul>
        </details>
      </div>
    </section>
  );
}

function StoppedPanel({ run }: { run: WorkflowRun }) {
  const rejected = run.status === "rejected";
  return (
    <section className="overflow-hidden rounded-2xl border border-rose-300/18 bg-rose-300/[0.035]">
      <div className="flex items-start gap-3 border-b border-rose-300/10 px-5 py-4">
        <div className="grid size-9 place-items-center rounded-xl border border-rose-300/18 bg-rose-300/[0.08] text-rose-200">
          {rejected ? <XCircle className="size-4" /> : <TriangleAlert className="size-4" />}
        </div>
        <div>
          <p className="font-mono text-[9px] uppercase tracking-[0.16em] text-rose-200/50">
            {rejected ? "Human decision" : "Fail-closed boundary"}
          </p>
          <h2 className="mt-1 text-sm font-semibold text-white/85">
            {rejected ? "Plan rejected" : "Workflow stopped safely"}
          </h2>
          <p className="mt-1 text-[9px] leading-4 text-white/32">
            {rejected
              ? "No remediation was executed. Evidence remains available to command."
              : "An agent or validation boundary failed. Unplanned work was not attempted."}
          </p>
        </div>
      </div>
      <div className="px-5 py-4">
        <PlanSummary run={run} />
      </div>
    </section>
  );
}

export function DecisionPanel(props: DecisionPanelProps) {
  if (props.run.status === "awaiting_approval") {
    return <AwaitingApproval {...props} />;
  }
  if (props.run.status === "completed") {
    return <ResolvedPanel run={props.run} />;
  }
  return <StoppedPanel run={props.run} />;
}
