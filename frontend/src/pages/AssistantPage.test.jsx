import { act, fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { createChatServer } from "../test/chatServer";
import { fixtures } from "../test/chatResponses";
import { renderAssistant } from "../test/renderAssistant";

const CANCEL_TEXT = "Stopped waiting; the server may still finish this request.";
const WAIT_TEXT = "Some questions take longer while the research engine initializes or retrieves additional information.";
const SUGGESTIONS = [
  "Who won the 2023 Medicine prize and what did they discover?",
  "Explain click chemistry in simple terms.",
  "Which three birth countries have the most Nobel laureates?",
  "Why did Albert Einstein receive the Nobel Prize?",
];

// Lets the fetch -> text -> JSON.parse chain settle without real timers.
const settle = () => act(async () => {
  for (let i = 0; i < 20; i += 1) await Promise.resolve();
});

let server;
beforeEach(() => {
  server = createChatServer();
});
afterEach(() => {
  vi.unstubAllGlobals();
});

describe("initial page", () => {
  it("renders a minimal page: title, one subtitle, four suggestions and the composer, with no disclaimer below the input", () => {
    const { textarea, askButton } = renderAssistant();
    expect(screen.getByRole("heading", { level: 1, name: "Nobel Intelligence" })).toBeInTheDocument();
    expect(screen.getByText("Discover the people, ideas and science that changed our world.")).toBeInTheDocument();
    expect(screen.queryByText(/Nobel Explorer currently covers Nobel Prize records/)).not.toBeInTheDocument();
    expect(screen.queryByText(/AI-generated answers may contain errors/)).not.toBeInTheDocument();
    const suggestions = within(screen.getByRole("region", { name: "Try a question" })).getAllByRole("button");
    expect(suggestions.map((b) => b.textContent)).toEqual(SUGGESTIONS);
    expect(textarea()).toHaveValue("");
    expect(textarea()).toHaveAccessibleDescription(/Press Enter to ask, Shift\+Enter for a new line\. 0 \/ 1,000 characters/);
    expect(screen.getByText("0 / 1,000 characters")).toHaveClass("visually-hidden");
    expect(askButton()).toBeDisabled();
    expect(screen.queryByRole("button", { name: "Clear conversation" })).not.toBeInTheDocument();
    expect(server.fetchMock).not.toHaveBeenCalled();
  });

  it("keeps the decorative illustration throughout; the page switches to the compact conversation layout", async () => {
    const { user, ask } = renderAssistant();
    const art = () => document.querySelector(".assistant-welcome-art");
    const page = () => document.querySelector(".assistant-page");
    expect(art()).toHaveAttribute("aria-hidden", "true");
    expect(page()).not.toHaveClass("assistant-page--active");
    await ask("Who won?");
    expect(art()).toBeInTheDocument();
    expect(page()).toHaveClass("assistant-page--active"); // scaled to 65% by assistant.css
    await user.click(screen.getByRole("button", { name: "Clear conversation" }));
    expect(art()).toBeInTheDocument();
    expect(page()).not.toHaveClass("assistant-page--active");
  });

  it("hides the suggestions once a conversation starts and shows Clear conversation", async () => {
    const { ask } = renderAssistant();
    await ask("Who won?");
    expect(screen.queryByRole("region", { name: "Try a question" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Clear conversation" })).toBeEnabled();
  });

  it("does not use browser storage", () => {
    const setItem = vi.spyOn(Storage.prototype, "setItem");
    renderAssistant();
    expect(setItem).not.toHaveBeenCalled();
  });
});

describe("composer", () => {
  it("fills the composer from a suggestion and focuses it without sending", async () => {
    const { user, textarea } = renderAssistant();
    await user.click(screen.getByRole("button", { name: SUGGESTIONS[1] }));
    expect(textarea()).toHaveValue(SUGGESTIONS[1]);
    expect(textarea()).toHaveFocus();
    expect(server.fetchMock).not.toHaveBeenCalled();
  });

  it("refuses blank questions", async () => {
    const { user, textarea, askButton } = renderAssistant();
    await user.type(textarea(), "   ");
    expect(askButton()).toBeDisabled();
    await user.keyboard("{Enter}");
    fireEvent.submit(textarea().form);
    expect(server.fetchMock).not.toHaveBeenCalled();
  });

  it("enforces the 1,000-character limit", async () => {
    const { user, textarea, askButton } = renderAssistant();
    await user.click(textarea());
    await user.paste("x".repeat(1000));
    expect(askButton()).toBeEnabled();
    expect(screen.getByText("1,000 / 1,000 characters")).toBeInTheDocument();
    expect(screen.getByText("1,000 / 1,000 characters")).not.toHaveClass("visually-hidden"); // shown near the limit
    await user.paste("y");
    expect(askButton()).toBeDisabled();
    expect(textarea()).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByText(/1,001 \/ 1,000 characters — please shorten your question/)).toBeInTheDocument();
    await user.keyboard("{Enter}");
    expect(server.fetchMock).not.toHaveBeenCalled();
  });

  it("submits on Enter and inserts a newline on Shift+Enter", async () => {
    const { user, textarea } = renderAssistant();
    await user.type(textarea(), "Line one{Shift>}{Enter}{/Shift}line two");
    expect(textarea()).toHaveValue("Line one\nline two");
    expect(server.fetchMock).not.toHaveBeenCalled();
    await user.keyboard("{Enter}");
    expect(server.fetchMock).toHaveBeenCalledTimes(1);
    expect(server.last.body).toEqual({ question: "Line one\nline two" });
  });

  it("ignores Enter while an IME composition is active", async () => {
    const { user, textarea } = renderAssistant();
    await user.type(textarea(), "東京");
    fireEvent.keyDown(textarea(), { key: "Enter", isComposing: true });
    fireEvent.keyDown(textarea(), { key: "Enter", keyCode: 229 });
    expect(server.fetchMock).not.toHaveBeenCalled();
    fireEvent.keyDown(textarea(), { key: "Enter" });
    expect(server.fetchMock).toHaveBeenCalledTimes(1);
  });

  it("sends exactly one request for rapid repeated submissions", async () => {
    const { user, textarea } = renderAssistant();
    await user.type(textarea(), "Who won?");
    fireEvent.keyDown(textarea(), { key: "Enter" });
    fireEvent.keyDown(textarea(), { key: "Enter" });
    fireEvent.submit(textarea().form);
    await user.click(screen.getByRole("button", { name: "Asking…" }));
    expect(server.fetchMock).toHaveBeenCalledTimes(1);
  });
});

describe("request lifecycle", () => {
  it("shows a loading state while waiting and announces it once", async () => {
    const { ask, textarea, announcer, conversation } = renderAssistant();
    await ask("Who won the 2022 Chemistry prize?");
    expect(conversation().getByText("Searching Nobel Explorer records…")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Asking…" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Cancel" })).toBeEnabled();
    expect(textarea()).toHaveValue("");
    expect(announcer()).toHaveTextContent("Searching Nobel Explorer records…");
  });

  it("shows and announces the extended-wait message once, at eight seconds (regression: timer is silent)", async () => {
    vi.useFakeTimers();
    const { askNow, announcer, conversation } = renderAssistant();
    askNow("Who won?");
    const pending = conversation().getByText("Searching Nobel Explorer records…");
    expect(pending.closest("[aria-live], [role=status], [role=log], [role=alert]")).toBeNull();

    const announcements = [];
    const observer = new MutationObserver(() => announcements.push(announcer().textContent));
    observer.observe(announcer(), { childList: true, characterData: true, subtree: true });

    await act(async () => vi.advanceTimersByTime(7000));
    expect(screen.getByText("7s")).toBeInTheDocument();
    expect(screen.queryByText(WAIT_TEXT)).not.toBeInTheDocument();
    await act(async () => vi.advanceTimersByTime(1000));
    expect(conversation().getByText(WAIT_TEXT)).toBeInTheDocument();
    await act(async () => vi.advanceTimersByTime(5000));
    observer.disconnect();
    expect(announcements).toEqual([WAIT_TEXT]);
  });

  it("starts each request with a fresh elapsed time (regression: stale 8 s state from the previous request)", async () => {
    vi.useFakeTimers();
    const { askNow, announcer, conversation } = renderAssistant();
    askNow("First, slow question");
    await act(async () => vi.advanceTimersByTime(8500));
    expect(conversation().getByText(WAIT_TEXT)).toBeInTheDocument();
    server.last.respond(200, fixtures["real-r04"]);
    await settle();
    expect(screen.queryByText(WAIT_TEXT)).not.toBeInTheDocument();

    // Record every visible state and announcement while the second request starts.
    const seen = [];
    const record = () => seen.push({ wait: !!document.querySelector(".assistant-extended-wait"), announcement: announcer().textContent });
    const observer = new MutationObserver(record);
    observer.observe(document.body, { childList: true, subtree: true, characterData: true });
    askNow("Second question");
    await settle();
    expect(seen.length).toBeGreaterThan(0);
    expect(seen.every((state) => !state.wait)).toBe(true);
    expect(seen.map((state) => state.announcement)).not.toContain(WAIT_TEXT);
    expect(conversation().getAllByText("0s").length).toBeGreaterThan(0);
    expect(announcer()).toHaveTextContent("Searching Nobel Explorer records…");

    await act(async () => vi.advanceTimersByTime(7000));
    expect(screen.queryByText(WAIT_TEXT)).not.toBeInTheDocument();
    await act(async () => vi.advanceTimersByTime(1000));
    observer.disconnect();
    expect(conversation().getByText(WAIT_TEXT)).toBeInTheDocument();
    expect(announcer()).toHaveTextContent(WAIT_TEXT);
  });

  it("resets elapsed time after cancel and clear", async () => {
    vi.useFakeTimers();
    const { askNow, conversation } = renderAssistant();
    askNow("Slow one");
    await act(async () => vi.advanceTimersByTime(9000));
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    askNow("Next one");
    await settle();
    expect(screen.queryByText(WAIT_TEXT)).not.toBeInTheDocument();
    expect(conversation().getByText("0s")).toBeInTheDocument();
    await act(async () => vi.advanceTimersByTime(9000));
    fireEvent.click(screen.getByRole("button", { name: "Clear conversation" }));
    askNow("After clear");
    await settle();
    expect(screen.queryByText(WAIT_TEXT)).not.toBeInTheDocument();
    expect(conversation().getByText("0s")).toBeInTheDocument();
  });

  it("renders the answer and stops the timer when the response arrives", async () => {
    vi.useFakeTimers();
    const { askNow } = renderAssistant();
    askNow("Who won the 2023 Medicine prize and what did they discover?");
    expect(vi.getTimerCount()).toBeGreaterThan(0);
    server.last.respond(200, fixtures["real-r04"]);
    await settle();
    expect(document.querySelector(".assistant-answer-text")).toHaveTextContent(/Katalin Karikó and Drew Weissman shared/);
    expect(document.querySelector(".assistant-pending")).toBeNull();
    expect(vi.getTimerCount()).toBe(0);
  });

  it("cancels: shows the exact message, restores the question and ignores the late response", async () => {
    const { user, ask, textarea, announcer, conversation } = renderAssistant();
    await ask("Slow question");
    const request = server.last;
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(request.aborted).toBe(true);
    expect(conversation().getByText(CANCEL_TEXT)).toBeInTheDocument();
    expect(announcer()).toHaveTextContent(CANCEL_TEXT);
    expect(textarea()).toHaveValue("Slow question");
    request.respond(200, { ...fixtures["real-r04"], answer: "LATE ANSWER [E1]" });
    await settle();
    expect(screen.queryByText(/LATE ANSWER/)).not.toBeInTheDocument();
  });

  it("clears during a request: empties the conversation, focuses the input and ignores the late response", async () => {
    const { user, ask, textarea, announcer } = renderAssistant();
    await ask("Slow question");
    const request = server.last;
    await user.click(screen.getByRole("button", { name: "Clear conversation" }));
    expect(request.aborted).toBe(true);
    expect(screen.queryByText("You asked")).not.toBeInTheDocument();
    expect(textarea()).toHaveValue("");
    expect(textarea()).toHaveFocus();
    expect(announcer()).toHaveTextContent("Conversation cleared.");
    request.respond(200, { ...fixtures["real-r04"], answer: "LATE ANSWER [E1]" });
    await settle();
    expect(screen.queryByText(/LATE ANSWER/)).not.toBeInTheDocument();
    expect(screen.queryByRole("article")).not.toBeInTheDocument();
  });

  it("ignores a late response from an earlier request once a newer request is active", async () => {
    const { user, ask, conversation } = renderAssistant();
    await ask("First question");
    const first = server.last;
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    await ask("Second question");
    const second = server.last;
    first.respond(200, { ...fixtures["real-r04"], answer: "FIRST LATE ANSWER" });
    await settle();
    expect(screen.queryByText("FIRST LATE ANSWER")).not.toBeInTheDocument();
    expect(conversation().getByText("Searching Nobel Explorer records…")).toBeInTheDocument();
    second.respond(200, { ...fixtures["real-r04"], answer: "SECOND ANSWER" });
    expect(await screen.findByText("SECOND ANSWER")).toBeInTheDocument();
    const articles = screen.getAllByRole("article");
    expect(articles).toHaveLength(2);
    expect(within(articles[0]).getByText(CANCEL_TEXT)).toBeInTheDocument();
  });

  it("aborts the request and clears timers on unmount", async () => {
    vi.useFakeTimers();
    const { askNow, unmount } = renderAssistant();
    askNow("Slow question");
    const request = server.last;
    unmount();
    expect(request.aborted).toBe(true);
    expect(vi.getTimerCount()).toBe(0);
    request.respond(200, fixtures["real-r04"]);
    await settle();
  });

  it("restores the question after a failure when the input is empty", async () => {
    const { ask, textarea } = renderAssistant();
    await ask("Who won?");
    server.last.failNetwork();
    expect(await screen.findByText("Could not reach the Nobel Explorer server")).toBeInTheDocument();
    expect(textarea()).toHaveValue("Who won?");
  });

  it("keeps a newly typed question when the earlier request fails", async () => {
    const { user, ask, textarea } = renderAssistant();
    await ask("Who won?");
    await user.type(textarea(), "My next question");
    server.last.failNetwork();
    expect(await screen.findByText("Could not reach the Nobel Explorer server")).toBeInTheDocument();
    expect(textarea()).toHaveValue("My next question");
  });

  it("does not move focus away from a user typing when an answer arrives", async () => {
    const { user, ask, textarea } = renderAssistant();
    await ask("Who won?");
    await user.type(textarea(), "Follow-up");
    server.last.respond(200, fixtures["real-r04"]);
    await waitFor(() => expect(document.querySelector(".assistant-answer-text")).toHaveTextContent(/Katalin Karikó and Drew Weissman shared/));
    expect(textarea()).toHaveFocus();
    expect(textarea()).toHaveValue("Follow-up");
  });
});

describe("status notices", () => {
  const errorBody = (status, error) => ({ ...fixtures.budget, status, answer: null, grounding: null, evidence_limitations: [], error });
  it.each([
    ["503 ChatResponse", 503, errorBody("unavailable", { type: "unavailable", message: "The AI research assistant is disabled (AI_AGENT_ENABLED is not true)." }),
      "The AI assistant is currently unavailable", "status"],
    ["503 {detail}", 503, { detail: "Invalid AI agent configuration (AI_AGENT_MAX_TOOL_CALLS): bad" },
      "The AI assistant is currently unavailable", "status"],
    ["422 list detail", 422, { detail: [{ msg: "String should have at least 1 character" }] },
      "The question could not be accepted", "alert"],
    ["422 string detail", 422, { detail: "question must be at most 1000 characters" },
      "The question could not be accepted", "alert"],
    ["502 provider error", 502, errorBody("error", { type: "provider_auth", message: "Incorrect API key provided: sk-abc...xyz" }),
      "The language model service had a problem", "alert"],
    ["500 internal error", 500, errorBody("error", { type: "internal", message: "KeyError: 'x' in service.py" }),
      "Something went wrong", "alert"],
    ["budget exhausted", 200, fixtures.budget, "The assistant reached its processing limit", "status"],
    ["timeout", 200, { ...fixtures.budget, status: "timeout" }, "The assistant ran out of time", "status"],
    ["malformed JSON", 200, "{not json", "Unexpected response", "alert"],
    ["unexpected shape", 200, { hello: "world" }, "Unexpected response", "alert"],
  ])("%s", async (_name, http, body, title, role) => {
    const { ask, container } = renderAssistant();
    await ask("Who won?");
    server.last.respond(http, body);
    const heading = await screen.findByText(title);
    expect(heading.closest(`[role="${role}"]`)).not.toBeNull();
    expect(container.textContent).not.toMatch(/sk-abc|AI_AGENT|KeyError|\[object Object\]|service\.py/);
  });

  it("shows the 422 message from the server", async () => {
    const { ask } = renderAssistant();
    await ask("Who won?");
    server.last.respond(422, { detail: "question must be at most 1000 characters" });
    expect(await screen.findByText("question must be at most 1000 characters")).toBeInTheDocument();
  });

  it("keeps the answer and limitations for budget-exhausted and timeout responses", async () => {
    const { ask } = renderAssistant();
    await ask("Who won?");
    server.last.respond(200, { ...fixtures.budget, status: "timeout" });
    expect(await screen.findByText(/I could not complete this request within the configured model-call limit/)).toBeInTheDocument();
    expect(screen.getByText("The assistant reached a processing limit before producing a final answer.")).toBeInTheDocument();
  });
});
