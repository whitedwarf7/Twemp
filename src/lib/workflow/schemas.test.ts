import { describe, expect, it } from "vitest";

import awaitingApprovalRun from "../../../contract-fixtures/awaiting-approval-run.json";
import completedRun from "../../../contract-fixtures/completed-run.json";
import rejectedRun from "../../../contract-fixtures/rejected-run.json";
import {
  ApprovalDecisionSchema,
  DEFAULT_INCIDENT,
  IncidentInputSchema,
  WorkflowRunSchema,
} from "@/lib/workflow/schemas";

function incident(overrides: Record<string, unknown> = {}) {
  return { ...DEFAULT_INCIDENT, ...overrides };
}

describe("backend contract compatibility", () => {
  // The fixtures are produced by the FastAPI engine, so these assertions prove the
  // TypeScript mirror still accepts real backend output.
  it.each([
    ["awaiting approval", awaitingApprovalRun],
    ["completed", completedRun],
    ["rejected", rejectedRun],
  ])("parses a real %s run", (_name, fixture) => {
    const parsed = WorkflowRunSchema.parse(fixture);

    expect(parsed.agents).toHaveLength(17);
    expect(parsed.metrics.agentsTotal).toBe(17);
    expect(parsed.events.length).toBeGreaterThan(0);
  });

  it("preserves the approval gate state from the backend", () => {
    const parsed = WorkflowRunSchema.parse(awaitingApprovalRun);

    expect(parsed.status).toBe("awaiting_approval");
    expect(parsed.approval?.status).toBe("pending");
    expect(parsed.plan?.actions.length).toBeGreaterThan(0);
    expect(parsed.events.some((event) => event.type === "remediation")).toBe(false);
  });

  it("preserves the resolved state from the backend", () => {
    const parsed = WorkflowRunSchema.parse(completedRun);

    expect(parsed.status).toBe("completed");
    expect(parsed.verification?.status).toBe("passed");
    expect(parsed.outcome?.followUps.length).toBeGreaterThan(0);
  });

  it("rejects a run whose event sequence is not a positive integer", () => {
    const broken = structuredClone(completedRun) as { events: { sequence: number }[] };
    broken.events[0].sequence = 0;

    expect(() => WorkflowRunSchema.parse(broken)).toThrow();
  });

  it("rejects a run carrying an unknown top-level field", () => {
    expect(() => WorkflowRunSchema.parse({ ...completedRun, injected: true })).toThrow();
  });

  it("rejects timestamps that are not ISO-8601 with a Z suffix", () => {
    const broken = structuredClone(completedRun) as { startedAt: string };
    broken.startedAt = "25/08/2026 06:58";

    expect(() => WorkflowRunSchema.parse(broken)).toThrow();
  });

  it("rejects a confidence value outside the unit interval", () => {
    const broken = structuredClone(completedRun) as { metrics: { confidence: number } };
    broken.metrics.confidence = 1.4;

    expect(() => WorkflowRunSchema.parse(broken)).toThrow();
  });
});

describe("IncidentInputSchema", () => {
  it("accepts the shipped default incident", () => {
    expect(IncidentInputSchema.parse(DEFAULT_INCIDENT)).toEqual(DEFAULT_INCIDENT);
  });

  it.each([5, 120])("accepts a %i character title", (length) => {
    expect(IncidentInputSchema.parse(incident({ title: "t".repeat(length) })).title).toHaveLength(
      length,
    );
  });

  it.each([4, 121])("rejects a %i character title", (length) => {
    expect(() => IncidentInputSchema.parse(incident({ title: "t".repeat(length) }))).toThrow();
  });

  it.each(["a-b", "svc.name", "svc_name", "team/svc"])("accepts service %s", (service) => {
    expect(IncidentInputSchema.parse(incident({ service })).service).toBe(service);
  });

  it.each(["has space", "semi;colon", "a"])("rejects service %s", (service) => {
    expect(() => IncidentInputSchema.parse(incident({ service }))).toThrow();
  });

  it("rejects an unsupported severity", () => {
    expect(() => IncidentInputSchema.parse(incident({ severity: "SEV-9" }))).toThrow();
  });

  it("requires between one and twelve signals", () => {
    expect(IncidentInputSchema.parse(incident({ signals: ["p95 latency high"] })).signals).toEqual([
      "p95 latency high",
    ]);
    expect(() => IncidentInputSchema.parse(incident({ signals: [] }))).toThrow();
    expect(() =>
      IncidentInputSchema.parse(incident({ signals: Array.from({ length: 13 }, () => "signal") })),
    ).toThrow();
  });

  it("rejects a description shorter than the backend minimum", () => {
    expect(() => IncidentInputSchema.parse(incident({ description: "too short" }))).toThrow();
  });

  it("trims surrounding whitespace like the backend does", () => {
    const parsed = IncidentInputSchema.parse(
      incident({ title: "  Checkout latency surge  ", region: "  eu-central  " }),
    );

    expect(parsed.title).toBe("Checkout latency surge");
    expect(parsed.region).toBe("eu-central");
  });

  it("rejects unknown fields so typos fail fast", () => {
    expect(() => IncidentInputSchema.parse(incident({ runbook: "delete-db" }))).toThrow();
  });
});

describe("ApprovalDecisionSchema", () => {
  it("defaults the note to an empty string", () => {
    expect(ApprovalDecisionSchema.parse({ decision: "approve", reviewer: "On-call" }).note).toBe("");
  });

  it("trims the reviewer and note", () => {
    const parsed = ApprovalDecisionSchema.parse({
      decision: "reject",
      reviewer: "  On-call  ",
      note: "  Too broad  ",
    });

    expect(parsed.reviewer).toBe("On-call");
    expect(parsed.note).toBe("Too broad");
  });

  it("enforces the reviewer length after trimming", () => {
    expect(() => ApprovalDecisionSchema.parse({ decision: "approve", reviewer: " a " })).toThrow();
    expect(() =>
      ApprovalDecisionSchema.parse({ decision: "approve", reviewer: "r".repeat(81) }),
    ).toThrow();
  });

  it("caps the note length", () => {
    expect(() =>
      ApprovalDecisionSchema.parse({
        decision: "approve",
        reviewer: "On-call",
        note: "n".repeat(501),
      }),
    ).toThrow();
  });

  it("only allows approve or reject", () => {
    expect(() => ApprovalDecisionSchema.parse({ decision: "maybe", reviewer: "On-call" })).toThrow();
  });
});
