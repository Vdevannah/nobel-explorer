import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";

// Smoke tests for the application shell. Existing pages are not re-tested in
// depth: every API request fails with 503 so each page must render its own
// heading or error state without crashing, and no page except the assistant
// may call the AI endpoint.
let fetchMock;
beforeEach(() => {
  fetchMock = vi.fn(async () => new Response(JSON.stringify({ detail: "Service unavailable in tests" }), { status: 503 }));
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => {
  vi.unstubAllGlobals();
});

function renderAt(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

const aiCalls = () => fetchMock.mock.calls.filter(([url]) => String(url).includes("/ai/"));

describe("application shell", () => {
  it("shows every primary navigation link, including Ask AI", () => {
    renderAt("/");
    const nav = within(screen.getByRole("navigation", { name: "Primary navigation" }));
    expect(nav.getAllByRole("link").map((link) => link.textContent)).toEqual([
      "", "Home", "Explore Prizes", "Browse Laureates", "Analytics", "Learn", "Quiz", "Ask AI",
    ]);
    expect(nav.getByRole("link", { name: "Ask AI" })).toHaveAttribute("href", "/assistant");
    expect(nav.getByRole("button", { name: "Dark theme" })).toBeInTheDocument();
  });

  it.each([
    ["/", /Discover the greatest minds/],
    ["/prizes", "Explore Nobel Prizes"],
    ["/laureates", "Explore Nobel Laureates"],
    ["/analytics", "Analytics are temporarily unavailable."], // the failed request leads to its error state
    ["/learn", "Learn Nobel-winning science at your level."],
    ["/quiz", "Test your knowledge"],
    ["/assistant", "Nobel Intelligence"],
    ["/no-such-page", "This discovery is still waiting to be made."],
  ])("renders %s without crashing", async (path, heading) => {
    renderAt(path);
    expect(await screen.findByRole("heading", { level: 1, name: heading })).toBeInTheDocument();
    expect(aiCalls()).toHaveLength(0);
  });

  it("navigates to the assistant from the navbar and marks the link as current", async () => {
    const user = userEvent.setup();
    renderAt("/");
    await user.click(screen.getByRole("link", { name: "Ask AI" }));
    expect(await screen.findByRole("heading", { level: 1, name: "Nobel Intelligence" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ask AI" })).toHaveAttribute("aria-current", "page");
    expect(aiCalls()).toHaveLength(0);
  });

  it("leaves the assistant mid-request without errors and aborts the request", async () => {
    let signal;
    fetchMock.mockImplementation((url, init) => {
      if (String(url).includes("/ai/chat")) {
        signal = init.signal;
        return new Promise(() => {});
      }
      return Promise.resolve(new Response("{}", { status: 503 }));
    });
    const consoleError = vi.spyOn(console, "error");
    const user = userEvent.setup();
    renderAt("/assistant");
    await user.type(screen.getByLabelText("Your question"), "Who won?{Enter}");
    expect(aiCalls()).toHaveLength(1);
    await user.click(screen.getByRole("link", { name: "Quiz" }));
    expect(await screen.findByRole("heading", { level: 1, name: "Test your knowledge" })).toBeInTheDocument();
    expect(signal.aborted).toBe(true);
    expect(consoleError).not.toHaveBeenCalled();
  });
});
