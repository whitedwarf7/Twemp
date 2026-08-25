"use client";

import { useState } from "react";

import { ActivityFeed } from "@/components/activity-feed";
import { AgentTopology } from "@/components/agent-topology";
import { DecisionPanel } from "@/components/decision-panel";
import { IncidentBrief } from "@/components/incident-brief";
import { IncidentIntake } from "@/components/incident-intake";
import { IncidentOverview } from "@/components/incident-overview";
import { TopBar } from "@/components/top-bar";
import { startWorkflow as requestWorkflow, submitDecision } from "@/lib/api-client";
import {
  DEFAULT_INCIDENT,
  type ApprovalDecision,
  type IncidentInput,
  type WorkflowRun,
} from "@/lib/workflow/schemas";

function freshIncident(): IncidentInput {
  return { ...DEFAULT_INCIDENT, signals: [...DEFAULT_INCIDENT.signals] };
}

export function CommandCenter() {
  const [draft, setDraft] = useState<IncidentInput>(freshIncident);
  const [run, setRun] = useState<WorkflowRun | null>(null);
  const [isStarting, setIsStarting] = useState(false);
  const [isDeciding, setIsDeciding] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [decisionError, setDecisionError] = useState<string | null>(null);

  const startWorkflow = async () => {
    setError(null);
    setIsStarting(true);
    try {
      const [workflow] = await Promise.all([
        requestWorkflow(draft),
        new Promise((resolve) => window.setTimeout(resolve, 650)),
      ]);
      setRun(workflow);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to start the workflow");
    } finally {
      setIsStarting(false);
    }
  };

  const decide = async (decision: ApprovalDecision) => {
    if (!run) return;
    setDecisionError(null);
    setIsDeciding(true);
    try {
      setRun(await submitDecision(run.id, decision));
    } catch (caught) {
      setDecisionError(
        caught instanceof Error ? caught.message : "Unable to record the approval decision",
      );
    } finally {
      setIsDeciding(false);
    }
  };

  const reset = () => {
    setRun(null);
    setDraft(freshIncident());
    setError(null);
    setDecisionError(null);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <div className="min-h-screen bg-[#07100e] text-white selection:bg-emerald-300/25">
      <TopBar run={run} onReset={reset} />
      {!run ? (
        <IncidentIntake
          draft={draft}
          isStarting={isStarting}
          error={error}
          onChange={(patch) => setDraft((current) => ({ ...current, ...patch }))}
          onStart={startWorkflow}
        />
      ) : (
        <main className="relative mx-auto w-full max-w-[1680px] px-4 pb-12 pt-5 sm:px-6 lg:px-8">
          <div className="pointer-events-none fixed inset-0 -z-10 bg-[radial-gradient(circle_at_22%_0%,rgba(110,231,183,0.035),transparent_28%),radial-gradient(circle_at_88%_40%,rgba(34,211,238,0.025),transparent_25%)]" />
          <IncidentOverview run={run} />

          <div className="mt-3 grid items-start gap-3 xl:grid-cols-[minmax(0,1.58fr)_minmax(350px,0.72fr)]">
            <div className="min-w-0 space-y-3">
              <AgentTopology run={run} />
              <ActivityFeed run={run} />
            </div>
            <aside className="space-y-3 xl:sticky xl:top-[76px]">
              <DecisionPanel
                run={run}
                isDeciding={isDeciding}
                error={decisionError}
                onDecision={decide}
              />
              <IncidentBrief run={run} />
            </aside>
          </div>

          <footer className="mt-6 flex flex-col gap-2 border-t border-white/[0.05] py-5 text-[9px] text-white/20 sm:flex-row sm:items-center sm:justify-between">
            <p>Twemp reference workflow · FastAPI orchestration · provider-neutral</p>
            <p className="font-mono uppercase tracking-[0.12em]">
              No external remediation adapter connected
            </p>
          </footer>
        </main>
      )}
    </div>
  );
}
