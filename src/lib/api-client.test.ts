import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import completedRun from "../../contract-fixtures/completed-run.json";
import awaitingApprovalRun from "../../contract-fixtures/awaiting-approval-run.json";
import { API_BASE_URL, ApiError, startWorkflow, submitDecision } from "@/lib/api-client";
import { DEFAULT_INCIDENT, type ApprovalDecision } from "@/lib/workflow/schemas";

const APPROVAL: ApprovalDecision = {
  decision: "approve",
  reviewer: "Primary on-call",
  note: "Reviewed",
};

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

function mockFetch(response: Response | Error) {
  const fetchMock = vi.fn(async () => {
    if (response instanceof Error) {
      throw response;
    }
    return response;
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

beforeEach(() => {
  vi.unstubAllGlobals();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("configuration", () => {
  it("targets the backend without a trailing slash", () => {
    expect(API_BASE_URL).not.toMatch(/\/$/);
    expect(API_BASE_URL).toMatch(/^https?:\/\//);
  });
});

describe("startWorkflow", () => {
  it("posts the validated incident as JSON to the workflow endpoint", async () => {
    const fetchMock = mockFetch(jsonResponse(awaitingApprovalRun, 201));

    await startWorkflow(DEFAULT_INCIDENT);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe(`${API_BASE_URL}/api/workflows`);
    expect(init.method).toBe("POST");
    expect(init.headers).toEqual({ "Content-Type": "application/json" });
    expect(JSON.parse(String(init.body))).toEqual(DEFAULT_INCIDENT);
  });

  it("returns the parsed workflow run", async () => {
    mockFetch(jsonResponse(awaitingApprovalRun, 201));

    const run = await startWorkflow(DEFAULT_INCIDENT);

    expect(run.status).toBe("awaiting_approval");
    expect(run.agents).toHaveLength(17);
  });

  it("validates the incident before touching the network", async () => {
    const fetchMock = mockFetch(jsonResponse(awaitingApprovalRun, 201));

    await expect(startWorkflow({ ...DEFAULT_INCIDENT, title: "no" })).rejects.toThrow();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("surfaces the first validation detail from the backend", async () => {
    mockFetch(
      jsonResponse(
        { error: "Request validation failed", details: ["severity: Input should be 'SEV-1'"] },
        400,
      ),
    );

    await expect(startWorkflow(DEFAULT_INCIDENT)).rejects.toThrow(
      "Request validation failed: severity: Input should be 'SEV-1'",
    );
  });

  it("surfaces a detail-free backend error message", async () => {
    mockFetch(jsonResponse({ error: "Workflow run not found" }, 404));

    await expect(startWorkflow(DEFAULT_INCIDENT)).rejects.toThrow("Workflow run not found");
  });

  it("falls back to the status code when the error body is unusable", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          ({
            ok: false,
            status: 502,
            json: async () => {
              throw new SyntaxError("Unexpected token");
            },
          }) as unknown as Response,
      ),
    );

    await expect(startWorkflow(DEFAULT_INCIDENT)).rejects.toThrow("Request failed (502)");
  });

  it("reports an unreachable backend with actionable guidance", async () => {
    mockFetch(new TypeError("fetch failed"));

    await expect(startWorkflow(DEFAULT_INCIDENT)).rejects.toThrow(
      "Cannot reach the Twemp API. Start the FastAPI backend and try again.",
    );
  });

  it("raises ApiError carrying the HTTP status", async () => {
    mockFetch(jsonResponse({ error: "Conflict" }, 409));

    await expect(startWorkflow(DEFAULT_INCIDENT)).rejects.toMatchObject({
      name: "ApiError",
      status: 409,
    });
    expect(new ApiError("boom", 500)).toBeInstanceOf(Error);
  });

  it("rejects a response that violates the workflow contract", async () => {
    mockFetch(jsonResponse({ id: "INC-1", status: "awaiting_approval" }, 201));

    await expect(startWorkflow(DEFAULT_INCIDENT)).rejects.toThrow();
  });
});

describe("submitDecision", () => {
  it("posts the decision to the run-scoped endpoint", async () => {
    const fetchMock = mockFetch(jsonResponse(completedRun));

    const run = await submitDecision("INC-FIXTURE", APPROVAL);

    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe(`${API_BASE_URL}/api/workflows/INC-FIXTURE/decision`);
    expect(JSON.parse(String(init.body))).toEqual(APPROVAL);
    expect(run.status).toBe("completed");
  });

  it("encodes run identifiers so they cannot alter the path", async () => {
    const fetchMock = mockFetch(jsonResponse(completedRun));

    await submitDecision("INC-1/../admin", APPROVAL);

    const [url] = fetchMock.mock.calls[0] as unknown as [string];
    expect(url).toBe(`${API_BASE_URL}/api/workflows/INC-1%2F..%2Fadmin/decision`);
  });

  it("applies the note default before sending", async () => {
    const fetchMock = mockFetch(jsonResponse(completedRun));

    await submitDecision("INC-FIXTURE", {
      decision: "reject",
      reviewer: "On-call",
    } as ApprovalDecision);

    const [, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(JSON.parse(String(init.body))).toEqual({
      decision: "reject",
      reviewer: "On-call",
      note: "",
    });
  });

  it("validates the decision before touching the network", async () => {
    const fetchMock = mockFetch(jsonResponse(completedRun));

    await expect(
      submitDecision("INC-FIXTURE", { ...APPROVAL, reviewer: "x" }),
    ).rejects.toThrow();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("propagates a conflict when the approval was already settled", async () => {
    mockFetch(
      jsonResponse({ error: "This workflow is not waiting for an approval decision" }, 409),
    );

    await expect(submitDecision("INC-FIXTURE", APPROVAL)).rejects.toThrow(
      "This workflow is not waiting for an approval decision",
    );
  });
});
