import { Check, Circle, LoaderCircle, LockKeyhole, X } from "lucide-react";

import { cn } from "@/lib/cn";
import type {
  AgentStatus,
  Team,
  WorkflowPhase,
  WorkflowStatus,
} from "@/lib/workflow/schemas";

export const TEAM_STYLES: Record<
  Team,
  { accent: string; border: string; bg: string; dot: string; label: string }
> = {
  command: {
    accent: "text-emerald-300",
    border: "border-emerald-400/25",
    bg: "bg-emerald-400/[0.07]",
    dot: "bg-emerald-300",
    label: "Command",
  },
  triage: {
    accent: "text-amber-300",
    border: "border-amber-400/20",
    bg: "bg-amber-400/[0.06]",
    dot: "bg-amber-300",
    label: "Triage",
  },
  investigation: {
    accent: "text-cyan-300",
    border: "border-cyan-400/20",
    bg: "bg-cyan-400/[0.06]",
    dot: "bg-cyan-300",
    label: "Investigation",
  },
  response: {
    accent: "text-violet-300",
    border: "border-violet-400/20",
    bg: "bg-violet-400/[0.06]",
    dot: "bg-violet-300",
    label: "Response",
  },
  communications: {
    accent: "text-rose-300",
    border: "border-rose-400/20",
    bg: "bg-rose-400/[0.06]",
    dot: "bg-rose-300",
    label: "Communications",
  },
};

export function AgentStatusIcon({ status }: { status: AgentStatus }) {
  const base = "size-3.5 shrink-0";
  if (status === "completed") {
    return <Check className={cn(base, "text-emerald-300")} strokeWidth={2.5} />;
  }
  if (status === "running") {
    return <LoaderCircle className={cn(base, "animate-spin text-cyan-300")} />;
  }
  if (status === "blocked") {
    return <LockKeyhole className={cn(base, "text-amber-300")} />;
  }
  if (status === "failed" || status === "cancelled") {
    return <X className={cn(base, "text-rose-300")} strokeWidth={2.5} />;
  }
  return <Circle className={cn(base, "text-white/25")} />;
}

const STATUS_COPY: Record<WorkflowStatus, string> = {
  running: "Orchestrating",
  awaiting_approval: "Awaiting approval",
  completed: "Resolved",
  rejected: "Plan rejected",
  failed: "Stopped safely",
};

export function WorkflowStatusPill({ status }: { status: WorkflowStatus }) {
  const tone = {
    running: "border-cyan-400/25 bg-cyan-400/10 text-cyan-200",
    awaiting_approval: "border-amber-400/25 bg-amber-400/10 text-amber-200",
    completed: "border-emerald-400/25 bg-emerald-400/10 text-emerald-200",
    rejected: "border-rose-400/25 bg-rose-400/10 text-rose-200",
    failed: "border-rose-400/25 bg-rose-400/10 text-rose-200",
  }[status];

  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 rounded-full border px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em]",
        tone,
      )}
    >
      <span className="relative flex size-1.5">
        {status === "running" && (
          <span className="absolute inline-flex size-full animate-ping rounded-full bg-current opacity-60" />
        )}
        <span className="relative inline-flex size-1.5 rounded-full bg-current" />
      </span>
      {STATUS_COPY[status]}
    </span>
  );
}

const PHASE_COPY: Record<WorkflowPhase, string> = {
  intake: "Intake",
  triage: "Triage",
  investigation: "Investigate",
  planning: "Plan",
  approval: "Approval gate",
  remediation: "Remediate",
  verification: "Verify",
  resolved: "Resolved",
  rejected: "Rejected",
  failed: "Failed",
};

export function PhaseLabel({ phase }: { phase: WorkflowPhase }) {
  return (
    <span className="font-mono text-[10px] uppercase tracking-[0.17em] text-white/40">
      {PHASE_COPY[phase]}
    </span>
  );
}
