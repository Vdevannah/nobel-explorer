import { afterEach, describe, expect, it, vi } from "vitest";

import { fixtures } from "../test/chatResponses";
import { API_BASE_URL, askResearchAssistant } from "./api";

const json = (status, body) => new Response(typeof body === "string" ? body : JSON.stringify(body), { status });

function stubFetch(impl) {
  const fetchMock = vi.fn(impl);
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("askResearchAssistant", () => {
  it("sends one POST to /ai/chat with a JSON body", async () => {
    const fetchMock = stubFetch(async () => json(200, fixtures["real-r04"]));
    const controller = new AbortController();
    await askResearchAssistant("Who won?", { signal: controller.signal });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(`${API_BASE_URL}/ai/chat`);
    expect(init.method).toBe("POST");
    expect(init.headers).toMatchObject({ "Content-Type": "application/json", Accept: "application/json" });
    expect(JSON.parse(init.body)).toEqual({ question: "Who won?" });
    expect(init.signal).toBe(controller.signal);
  });

  it.each([
    ["completed", 200, fixtures["real-r04"]],
    ["budget_exhausted", 200, fixtures.budget],
    ["timeout", 200, { ...fixtures.budget, status: "timeout" }],
  ])("returns the ChatResponse for %s", async (_status, http, body) => {
    stubFetch(async () => json(http, body));
    await expect(askResearchAssistant("q")).resolves.toEqual({ kind: "response", httpStatus: http, response: body });
  });

  it("keeps a 503 ChatResponse (disabled or unconfigured)", async () => {
    const body = { ...fixtures.budget, status: "unavailable", answer: null, error: { type: "unavailable", message: "disabled" } };
    stubFetch(async () => json(503, body));
    await expect(askResearchAssistant("q")).resolves.toEqual({ kind: "response", httpStatus: 503, response: body });
  });

  it("maps the 503 {detail} configuration error to unavailable without the detail", async () => {
    stubFetch(async () => json(503, { detail: "Invalid AI agent configuration (AI_AGENT_MAX_TOOL_CALLS): bad" }));
    const result = await askResearchAssistant("q");
    expect(result).toEqual({ kind: "unavailable", httpStatus: 503 });
    expect(JSON.stringify(result)).not.toContain("AI_AGENT");
  });

  it.each([
    [{ detail: "question must be at most 1000 characters" }, "question must be at most 1000 characters"],
    [{ detail: [{ msg: "String should have at least 1 character" }, { msg: "Second" }] }, "String should have at least 1 character Second"],
    [{ detail: [{ nope: 1 }] }, "The question could not be accepted. Please check it and try again."],
    [{ detail: { msg: "object" } }, "The question could not be accepted. Please check it and try again."],
    [{}, "The question could not be accepted. Please check it and try again."],
  ])("maps 422 %j to a readable message", async (body, message) => {
    stubFetch(async () => json(422, body));
    const result = await askResearchAssistant("q");
    expect(result).toEqual({ kind: "validation_error", httpStatus: 422, message });
    expect(result.message).not.toContain("[object Object]");
  });

  it.each([
    [502, { type: "provider_auth", message: "Incorrect API key provided: sk-abc...xyz" }],
    [500, { type: "internal", message: "boom" }],
  ])("keeps %i error ChatResponses (rendering hides diagnostics)", async (http, error) => {
    const body = { ...fixtures.budget, status: "error", answer: null, error };
    stubFetch(async () => json(http, body));
    await expect(askResearchAssistant("q")).resolves.toMatchObject({ kind: "response", httpStatus: http });
  });

  it("reports network errors", async () => {
    stubFetch(async () => {
      throw new TypeError("Failed to fetch");
    });
    await expect(askResearchAssistant("q")).resolves.toEqual({ kind: "network_error" });
  });

  it("reports aborted requests", async () => {
    const controller = new AbortController();
    stubFetch(async (_url, init) => {
      controller.abort();
      throw new DOMException("aborted", "AbortError");
    });
    await expect(askResearchAssistant("q", { signal: controller.signal })).resolves.toEqual({ kind: "aborted" });
  });

  it("reports an abort while reading the body as aborted", async () => {
    const controller = new AbortController();
    stubFetch(async () => ({
      status: 200,
      text: async () => {
        controller.abort();
        throw new DOMException("aborted", "AbortError");
      },
    }));
    await expect(askResearchAssistant("q", { signal: controller.signal })).resolves.toEqual({ kind: "aborted" });
  });

  it.each([
    [200, "not json", "malformed_response"],
    [200, "<html>oops</html>", "malformed_response"],
    [404, "<html>Not found</html>", "malformed_response"],
    [200, { hello: "world" }, "unexpected_response"],
    [200, { ...fixtures["real-r04"], status: "weird" }, "unexpected_response"],
    [200, { ...fixtures["real-r04"], citations: "nope" }, "unexpected_response"],
    [200, [], "unexpected_response"],
    [200, "", "unexpected_response"],
    [404, { detail: "Not Found" }, "unexpected_response"],
  ])("HTTP %i body %j -> %s", async (http, body, kind) => {
    stubFetch(async () => json(http, body));
    await expect(askResearchAssistant("q")).resolves.toMatchObject({ kind, httpStatus: http });
  });

  it("never retries automatically", async () => {
    const fetchMock = stubFetch(async () => json(500, "boom"));
    await askResearchAssistant("q");
    const networkFetch = stubFetch(async () => {
      throw new TypeError("down");
    });
    await askResearchAssistant("q");
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(networkFetch).toHaveBeenCalledTimes(1);
  });
});
