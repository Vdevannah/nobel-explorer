import { vi } from "vitest";

// Controllable fake for window.fetch used by the assistant tests. Each call is
// recorded and stays pending until the test responds, so ordering, cancellation
// and late responses can be exercised deterministically. Like a real server, a
// pending request keeps its handle after the client aborts: the test can still
// "finish" it to simulate a late response.
export function createChatServer() {
  const requests = [];
  const fetchMock = vi.fn((url, init = {}) => new Promise((resolve, reject) => {
    const request = {
      url,
      init,
      body: init.body ? JSON.parse(init.body) : null,
      aborted: false,
      respond(status, body) {
        resolve(new Response(typeof body === "string" ? body : JSON.stringify(body), { status }));
      },
      failNetwork() {
        reject(new TypeError("Failed to fetch"));
      },
    };
    init.signal?.addEventListener("abort", () => {
      request.aborted = true;
      reject(new DOMException("The operation was aborted.", "AbortError"));
    });
    requests.push(request);
  }));
  vi.stubGlobal("fetch", fetchMock);
  return {
    fetchMock,
    requests,
    get last() {
      return requests.at(-1);
    },
  };
}
