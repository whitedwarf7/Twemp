import {
  ApprovalDecisionSchema,
  IncidentInputSchema,
  WorkflowRunSchema,
  type ApprovalDecision,
  type IncidentInput,
  type WorkflowRun,
} from "@/lib/workflow/schemas";

const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000"
).replace(/\/+$/, "");

class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function errorMessage(status: number, body: unknown): string {
  const candidate = body as { error?: unknown; details?: unknown } | null;
  const message =
    typeof candidate?.error === "string" ? candidate.error : `Request failed (${status})`;
  const details = Array.isArray(candidate?.details)
    ? candidate.details.filter((value): value is string => typeof value === "string")
    : [];

  return details.length ? `${message}: ${details[0]}` : message;
}

async function request(path: string, body: unknown): Promise<WorkflowRun> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw new ApiError(
      "Cannot reach the Twemp API. Start the FastAPI backend and try again.",
      0,
    );
  }

  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(errorMessage(response.status, payload), response.status);
  }

  return WorkflowRunSchema.parse(payload);
}

// These stay `async` so validation failures reject the returned promise instead of
// throwing synchronously, which the Promise-typed signature would otherwise hide.
export async function startWorkflow(incident: IncidentInput): Promise<WorkflowRun> {
  return request("/api/workflows", IncidentInputSchema.parse(incident));
}

export async function submitDecision(
  runId: string,
  decision: ApprovalDecision,
): Promise<WorkflowRun> {
  return request(
    `/api/workflows/${encodeURIComponent(runId)}/decision`,
    ApprovalDecisionSchema.parse(decision),
  );
}

export { API_BASE_URL, ApiError };
