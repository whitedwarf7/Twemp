/**
 * Client-side mirror of the FastAPI workflow contract.
 *
 * The backend in `backend/app/workflow/schemas.py` is the source of truth; these schemas
 * validate responses at the network boundary and provide types for the UI.
 */
import { z } from "zod";

export const SeveritySchema = z.enum(["SEV-1", "SEV-2", "SEV-3"]);
export type Severity = z.infer<typeof SeveritySchema>;

export const TeamSchema = z.enum([
  "command",
  "triage",
  "investigation",
  "response",
  "communications",
]);
export type Team = z.infer<typeof TeamSchema>;

export const AgentRoleSchema = z.enum([
  "main-orchestrator",
  "sub-orchestrator",
  "specialist",
]);
export type AgentRole = z.infer<typeof AgentRoleSchema>;

export const AgentStatusSchema = z.enum([
  "queued",
  "running",
  "completed",
  "blocked",
  "cancelled",
  "failed",
]);
export type AgentStatus = z.infer<typeof AgentStatusSchema>;

export const WorkflowPhaseSchema = z.enum([
  "intake",
  "triage",
  "investigation",
  "planning",
  "approval",
  "remediation",
  "verification",
  "resolved",
  "rejected",
  "failed",
]);
export type WorkflowPhase = z.infer<typeof WorkflowPhaseSchema>;

export const WorkflowStatusSchema = z.enum([
  "running",
  "awaiting_approval",
  "completed",
  "rejected",
  "failed",
]);
export type WorkflowStatus = z.infer<typeof WorkflowStatusSchema>;

export const IncidentInputSchema = z
  .object({
    title: z.string().trim().min(5).max(120),
    description: z.string().trim().min(20).max(2_000),
    service: z
      .string()
      .trim()
      .min(2)
      .max(80)
      .regex(/^[a-zA-Z0-9._/-]+$/, "Use a service name without spaces"),
    severity: SeveritySchema,
    region: z.string().trim().min(2).max(80),
    signals: z.array(z.string().trim().min(3).max(240)).min(1).max(12),
  })
  .strict();
export type IncidentInput = z.infer<typeof IncidentInputSchema>;

export const AgentRuntimeSchema = z
  .object({
    id: z.string().min(1),
    name: z.string().min(1),
    shortName: z.string().min(1),
    role: AgentRoleSchema,
    team: TeamSchema,
    parentId: z.string().nullable(),
    mission: z.string().min(1),
    capabilities: z.array(z.string().min(1)).min(1),
    status: AgentStatusSchema,
    currentTask: z.string().nullable(),
    outputSummary: z.string().nullable(),
    startedAt: z.string().datetime().nullable(),
    completedAt: z.string().datetime().nullable(),
  })
  .strict();
export type AgentRuntime = z.infer<typeof AgentRuntimeSchema>;

export const FindingSeveritySchema = z.enum(["info", "warning", "critical"]);

export const AgentFindingSchema = z
  .object({
    id: z.string().min(1),
    agentId: z.string().min(1),
    team: TeamSchema,
    headline: z.string().min(3).max(160),
    detail: z.string().min(10).max(1_200),
    evidence: z.array(z.string().min(3).max(320)).min(1).max(8),
    confidence: z.number().min(0).max(1),
    severity: FindingSeveritySchema,
  })
  .strict();
export type AgentFinding = z.infer<typeof AgentFindingSchema>;

export const TeamReportSchema = z
  .object({
    id: z.string().min(1),
    orchestratorId: z.string().min(1),
    team: TeamSchema,
    title: z.string().min(3).max(160),
    summary: z.string().min(10).max(1_500),
    keyFindings: z.array(z.string().min(3).max(300)).min(1).max(8),
    recommendation: z.string().min(5).max(800),
    confidence: z.number().min(0).max(1),
  })
  .strict();
export type TeamReport = z.infer<typeof TeamReportSchema>;

export const RiskLevelSchema = z.enum(["low", "medium", "high"]);

export const RemediationActionSchema = z
  .object({
    id: z.string().min(1),
    title: z.string().min(3).max(160),
    detail: z.string().min(10).max(800),
    ownerAgentId: z.string().min(1),
    risk: RiskLevelSchema,
    reversible: z.boolean(),
    expectedSignal: z.string().min(5).max(400),
  })
  .strict();
export type RemediationAction = z.infer<typeof RemediationActionSchema>;

export const RemediationPlanSchema = z
  .object({
    id: z.string().min(1),
    hypothesis: z.string().min(10).max(1_000),
    summary: z.string().min(10).max(1_000),
    riskLevel: RiskLevelSchema,
    blastRadius: z.string().min(5).max(500),
    actions: z.array(RemediationActionSchema).min(1).max(8),
    rollback: z.string().min(10).max(800),
    validationChecks: z.array(z.string().min(5).max(320)).min(1).max(10),
  })
  .strict();
export type RemediationPlan = z.infer<typeof RemediationPlanSchema>;

export const ApprovalRequestSchema = z
  .object({
    id: z.string().min(1),
    status: z.enum(["pending", "approved", "rejected"]),
    requestedAt: z.string().datetime(),
    decidedAt: z.string().datetime().nullable(),
    decidedBy: z.string().nullable(),
    note: z.string().nullable(),
    plan: RemediationPlanSchema,
  })
  .strict();
export type ApprovalRequest = z.infer<typeof ApprovalRequestSchema>;

export const VerificationCheckSchema = z
  .object({
    label: z.string().min(3).max(160),
    value: z.string().min(1).max(120),
    status: z.enum(["passed", "failed"]),
    detail: z.string().min(3).max(400),
  })
  .strict();

export const VerificationReportSchema = z
  .object({
    status: z.enum(["passed", "failed"]),
    summary: z.string().min(10).max(1_000),
    checks: z.array(VerificationCheckSchema).min(1).max(10),
  })
  .strict();
export type VerificationReport = z.infer<typeof VerificationReportSchema>;

export const IncidentOutcomeSchema = z
  .object({
    rootCause: z.string().min(10).max(1_000),
    resolution: z.string().min(10).max(1_000),
    customerImpact: z.string().min(10).max(800),
    followUps: z.array(z.string().min(5).max(320)).min(1).max(10),
  })
  .strict();
export type IncidentOutcome = z.infer<typeof IncidentOutcomeSchema>;

export const WorkflowEventTypeSchema = z.enum([
  "workflow-started",
  "delegation",
  "agent-started",
  "finding",
  "synthesis",
  "plan-ready",
  "approval-requested",
  "approval-granted",
  "approval-rejected",
  "remediation",
  "verification",
  "communication",
  "workflow-completed",
  "workflow-failed",
]);
export type WorkflowEventType = z.infer<typeof WorkflowEventTypeSchema>;

export const WorkflowEventSchema = z
  .object({
    id: z.string().min(1),
    sequence: z.number().int().positive(),
    timestamp: z.string().datetime(),
    type: WorkflowEventTypeSchema,
    phase: WorkflowPhaseSchema,
    actorId: z.string().min(1),
    actorName: z.string().min(1),
    team: TeamSchema,
    title: z.string().min(3).max(160),
    detail: z.string().min(3).max(1_200),
    level: z.enum(["neutral", "success", "warning", "critical"]),
  })
  .strict();
export type WorkflowEvent = z.infer<typeof WorkflowEventSchema>;

export const WorkflowMetricsSchema = z
  .object({
    agentsTotal: z.number().int().nonnegative(),
    agentsCompleted: z.number().int().nonnegative(),
    activeAgents: z.number().int().nonnegative(),
    tasksCompleted: z.number().int().nonnegative(),
    handoffs: z.number().int().nonnegative(),
    confidence: z.number().min(0).max(1),
  })
  .strict();
export type WorkflowMetrics = z.infer<typeof WorkflowMetricsSchema>;

export const WorkflowRunSchema = z
  .object({
    id: z.string().min(1),
    incident: IncidentInputSchema,
    mode: z.enum(["demo", "openai"]),
    status: WorkflowStatusSchema,
    phase: WorkflowPhaseSchema,
    startedAt: z.string().datetime(),
    updatedAt: z.string().datetime(),
    agents: z.array(AgentRuntimeSchema),
    events: z.array(WorkflowEventSchema),
    findings: z.array(AgentFindingSchema),
    teamReports: z.array(TeamReportSchema),
    plan: RemediationPlanSchema.nullable(),
    approval: ApprovalRequestSchema.nullable(),
    verification: VerificationReportSchema.nullable(),
    outcome: IncidentOutcomeSchema.nullable(),
    metrics: WorkflowMetricsSchema,
  })
  .strict();
export type WorkflowRun = z.infer<typeof WorkflowRunSchema>;

export const ApprovalDecisionSchema = z
  .object({
    decision: z.enum(["approve", "reject"]),
    reviewer: z.string().trim().min(2).max(80),
    note: z.string().trim().max(500).default(""),
  })
  .strict();
export type ApprovalDecision = z.infer<typeof ApprovalDecisionSchema>;

export const ApiErrorSchema = z.object({
  error: z.string(),
  details: z.array(z.string()).optional(),
});
export type ApiError = z.infer<typeof ApiErrorSchema>;

export const DEFAULT_INCIDENT: IncidentInput = {
  title: "Checkout latency surge across EU region",
  description:
    "Checkout p95 latency climbed from 420 ms to 8.4 s shortly after the payment-router deployment. Error rate is 18% in eu-central and the retry queue continues to grow.",
  service: "payment-router",
  severity: "SEV-1",
  region: "eu-central",
  signals: [
    "p95 latency 8.4 s (baseline 420 ms)",
    "HTTP 5xx rate 18%",
    "payment retry queue 4.7× above baseline",
  ],
};
