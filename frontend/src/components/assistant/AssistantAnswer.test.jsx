import { act, fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { createChatServer } from "../../test/chatServer";
import { fixtures, replayedFixtures } from "../../test/chatResponses";
import { renderAssistant } from "../../test/renderAssistant";

let server;
beforeEach(() => {
  server = createChatServer();
});
afterEach(() => {
  vi.unstubAllGlobals();
});

async function answer(fixture, question = "Who won the 2023 Medicine prize and what did they discover?") {
  const page = renderAssistant();
  await page.ask(question);
  server.last.respond(200, typeof fixture === "string" ? fixtures[fixture] : fixture);
  await screen.findByRole("button", { name: "Copy answer" }).catch(() => {});
  return page;
}

const articles = () => screen.getAllByRole("article");
const evidenceToggle = (scope = document.body) => within(scope).getByRole("button", { name: /Cited evidence/ });
// The hidden attribute is what the component controls. Whether CSS honours it
// (the Phase 4C bug) is covered by styles/assistantStyles.test.js and the
// real-browser checks, because jsdom always treats [hidden] as display: none.
const isRendered = (element) => !element.hidden;
const toolsToggle = (scope = document.body) => within(scope).getByRole("button", { name: "How this answer was found" });

describe("evidence cards and provenance", () => {
  it("renders database records with source and an internal profile link that opens in a new tab", async () => {
    await answer("real-r04");
    const card = document.getElementById("assistant-exchange-1-evidence-E1");
    expect(within(card).getByText("Drew Weissman")).toBeInTheDocument();
    expect(within(card).getByText("Nobel Explorer database record")).toBeInTheDocument();
    expect(within(card).getByText("Source: Nobel Prize API v2.1 (imported by Nobel Explorer ETL)")).toBeInTheDocument();
    const link = within(card).getByRole("link", { name: /View laureate profile: Drew Weissman \(opens in a new tab\)/ });
    expect(link).toHaveAttribute("href", "/laureates/1024");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("renders a safe direct source link for source-linked evidence without calling it verified", async () => {
    await answer("real-r04");
    const card = document.getElementById("assistant-exchange-1-evidence-E3");
    expect(within(card).getByText("Linked source")).toBeInTheDocument();
    const link = within(card).getByRole("link", { name: /The Nobel Prize in Physiology or Medicine 2023 – Summary \(opens in a new tab\)/ });
    expect(link).toHaveAttribute("href", "https://www.nobelprize.org/prizes/medicine/2023/summary/");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
    expect(card.textContent).not.toMatch(/verified/i);
  });

  it("labels educational content as unverified and shows the related source as text only", async () => {
    await answer("real-r03", "Explain click chemistry in simple terms.");
    const card = document.getElementById("assistant-exchange-1-evidence-E1");
    expect(within(card).getByText("Nobel Explorer educational content")).toBeInTheDocument();
    expect(within(card).getByText("Not independently verified")).toBeInTheDocument();
    expect(within(card).getByText("Related context: The Nobel Prize in Chemistry 2022 – Summary")).toBeInTheDocument();
    expect(within(card).queryByRole("link")).not.toBeInTheDocument();
    expect(document.body.innerHTML).not.toContain("nobelprize.org/prizes/chemistry");
  });

  it("handles unknown provenance and unsafe or malformed records without links or crashes", async () => {
    await answer("malformed");
    const cards = document.querySelectorAll(".assistant-evidence-card");
    expect(cards).toHaveLength(6);
    expect(screen.getAllByText("Source not specified")).toHaveLength(2);
    expect(screen.queryByText(/DUPLICATE E1|BAD ID/)).not.toBeInTheDocument();
    const hrefs = [...document.querySelectorAll(".assistant-evidence-card a")].map((a) => a.getAttribute("href"));
    expect(hrefs).toHaveLength(2);
    expect(hrefs[0]).toMatch(/^https:\/\/www\.example\.org\//);
    expect(hrefs[1]).toBe("/laureates/2");
    expect(screen.getByText("Script source")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Script source|Cred source|PR source|Should not link/ })).not.toBeInTheDocument();
  });
});

describe("citations", () => {
  it("moves focus to the matching card, and re-expands a collapsed evidence section first", async () => {
    const { user } = await answer("real-r04");
    const [article] = articles();
    await user.click(within(article).getByRole("button", { name: "Evidence E3: Nucleoside Base Modifications and mRNA Vaccines" }));
    expect(document.getElementById("assistant-exchange-1-evidence-E3")).toHaveFocus();

    await user.click(evidenceToggle(article));
    expect(evidenceToggle(article)).toHaveAttribute("aria-expanded", "false");
    expect(isRendered(document.getElementById("assistant-exchange-1-evidence-list"))).toBe(false);

    await user.click(within(article).getByRole("button", { name: "Evidence E1: Drew Weissman" }));
    expect(evidenceToggle(article)).toHaveAttribute("aria-expanded", "true");
    expect(isRendered(document.getElementById("assistant-exchange-1-evidence-list"))).toBe(true);
    expect(document.getElementById("assistant-exchange-1-evidence-E1")).toHaveFocus();
  });

  it("activates citations from the keyboard", async () => {
    const { user } = await answer("real-r04");
    within(articles()[0]).getByRole("button", { name: "Evidence E2: Katalin Karikó" }).focus();
    await user.keyboard("{Enter}");
    expect(document.getElementById("assistant-exchange-1-evidence-E2")).toHaveFocus();
  });

  it("keeps citation targets separate across exchanges that both cite E1", async () => {
    const { user, ask } = await answer("real-r04");
    await ask("Second question");
    server.last.respond(200, fixtures["real-r04"]);
    await waitFor(() => expect(screen.getAllByRole("button", { name: "Copy answer" })).toHaveLength(2));

    const ids = [...document.querySelectorAll("[id]")].map((el) => el.id);
    expect(new Set(ids).size).toBe(ids.length);
    const second = articles()[1];
    const e1 = within(second).getByRole("button", { name: "Evidence E1: Drew Weissman" });
    expect(e1).toHaveAttribute("aria-controls", "assistant-exchange-2-evidence-E1");
    await user.click(e1);
    expect(document.getElementById("assistant-exchange-2-evidence-E1")).toHaveFocus();
  });

  it("keeps validation markers", async () => {
    await answer("partial");
    const [article] = articles();
    expect(within(article).getByText("[unverified]")).toBeInTheDocument();
    expect(within(article).getByText("[link removed]")).toBeInTheDocument();
  });

  it("leaves unknown evidence ids as plain text", async () => {
    await answer({ ...fixtures["real-r04"], answer: "Unknown [E9] and known [E1]." });
    const last = articles().at(-1);
    expect(within(last).queryByRole("button", { name: /Evidence E9/ })).not.toBeInTheDocument();
    expect(within(last).getByText("[E9]")).toBeInTheDocument();
  });
});

describe("grounding and limitations", () => {
  it.each([
    ["real-r04", "Includes evidence references"],
    ["partial", "Some references could not be validated"],
    ["real-r09", "No evidence references provided"],
    ["real-r06", "No supporting evidence retrieved"],
  ])("%s shows %s with the standing disclaimer", async (fixture, label) => {
    await answer(fixture);
    expect(screen.getByText(label)).toBeInTheDocument();
    expect(screen.getByText("Citations indicate referenced information but do not guarantee factual correctness.")).toBeInTheDocument();
  });

  it("does not classify null or unknown grounding values", async () => {
    await answer({ ...fixtures["real-r04"], grounding: "mystery" });
    expect(document.querySelector(".assistant-grounding-badge")).toBeNull();
    expect(screen.getByText(/do not guarantee factual correctness/)).toBeInTheDocument();
  });

  it("presents a correct abstention (no evidence) without an error notice", async () => {
    await answer("real-r06", "Who won the Nobel Prize in Mathematics in 1950?");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.getByText(/There is no Nobel Prize in Mathematics/)).toBeInTheDocument();
  });

  it("shows friendly, de-duplicated limitations instead of technical messages", async () => {
    await answer("real-r06");
    const limits = within(screen.getByRole("region", { name: "Limitations" }));
    expect(limits.getByText("Laureate search did not complete: the requested search parameters could not be processed.")).toBeInTheDocument();
    expect(limits.getByText("No supporting evidence was retrieved, so this answer is not based on Nobel Explorer data.")).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/validation_error|search_laureates:/);
  });

  it("de-duplicates repeated limitations", async () => {
    await answer("partial");
    expect(screen.getAllByText(/Links that did not come from Nobel Explorer's records were removed/)).toHaveLength(1);
  });

  it("translates the weak-match limitation", async () => {
    await answer("real-r09", "Explain sourdough fermentation.");
    expect(screen.getByText(/may not closely match this question/)).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/0\.40 threshold/);
  });
});

describe("tool activity", () => {
  it("is collapsed (actually hidden) by default and expands to friendly, allow-listed details", async () => {
    const { user } = await answer("real-r04");
    const toggle = toolsToggle();
    const panel = document.getElementById("assistant-exchange-1-tools-panel");
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(isRendered(panel)).toBe(false);

    await user.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(isRendered(panel)).toBe(true);
    const details = within(panel);
    expect(details.getByText("Search Nobel laureates")).toBeInTheDocument();
    expect(details.getByText("Search scientific knowledge")).toBeInTheDocument();
    expect(details.getByText("Physiology or Medicine")).toBeInTheDocument();
    expect(details.getByText("2 evidence references returned")).toBeInTheDocument();
    expect(details.getByText(/not the model's reasoning/)).toBeInTheDocument();
    expect(panel.textContent).not.toMatch(/call_|req-|latency|9572|gpt-6|\{/);
  });

  it("never shows ids, credentials, unknown tools' arguments or raw error types", async () => {
    const { user } = await answer("malformed");
    await user.click(toolsToggle());
    const text = document.getElementById("assistant-exchange-1-tools-panel").textContent;
    expect(text).toContain("Unrecognized tool");
    expect(text).toContain("Not run: the tool-call limit was reached");
    expect(text).not.toMatch(/FAKE-CREDENTIAL|HIDDEN_EXTRA|call_internal|rm_rf_tool|UNKNOWN TOOL QUERY|DROP TABLE|internal_error|unknown_tool/);
  });

  it("is omitted when there were no tool calls", async () => {
    await answer("hostile");
    expect(screen.queryByRole("button", { name: "How this answer was found" })).not.toBeInTheDocument();
  });
});

describe("copy answer", () => {
  function stubClipboard(writeText) {
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText } });
  }

  it("copies the original answer text with citation markers and confirms only after success", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    await answer("real-r04");
    stubClipboard(writeText);
    fireEvent.click(screen.getByRole("button", { name: "Copy answer" }));
    expect(await screen.findByText("Answer copied")).toHaveAttribute("role", "status");
    expect(writeText).toHaveBeenCalledWith(fixtures["real-r04"].answer);
  });

  it("reports a clipboard rejection without claiming success", async () => {
    await answer("real-r04");
    stubClipboard(vi.fn().mockRejectedValue(new DOMException("denied", "NotAllowedError")));
    fireEvent.click(screen.getByRole("button", { name: "Copy answer" }));
    expect(await screen.findByText("Could not copy. Select the answer text to copy it manually.")).toBeInTheDocument();
    expect(screen.queryByText("Answer copied")).not.toBeInTheDocument();
  });

  it("reports a missing Clipboard API as a failure", async () => {
    await answer("real-r04");
    stubClipboard(undefined);
    fireEvent.click(screen.getByRole("button", { name: "Copy answer" }));
    expect(await screen.findByText(/Could not copy/)).toBeInTheDocument();
  });

  it("clears the feedback after a short delay and cleans up its timer on unmount", async () => {
    const { unmount } = await answer("real-r04");
    stubClipboard(vi.fn().mockResolvedValue(undefined));
    vi.useFakeTimers();
    const flush = () => act(async () => {
      for (let i = 0; i < 5; i += 1) await Promise.resolve();
    });
    fireEvent.click(screen.getByRole("button", { name: "Copy answer" }));
    await flush();
    expect(screen.getByText("Answer copied")).toBeInTheDocument();
    await act(async () => vi.advanceTimersByTime(2500));
    expect(screen.queryByText("Answer copied")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Copy answer" }));
    await flush();
    expect(vi.getTimerCount()).toBe(1);
    const consoleError = vi.spyOn(console, "error");
    unmount();
    expect(vi.getTimerCount()).toBe(0);
    await act(async () => vi.advanceTimersByTime(5000));
    expect(consoleError).not.toHaveBeenCalled();
  });

  it("is not offered when there is no answer text", async () => {
    await answer({ ...fixtures["real-r04"], answer: "   " });
    expect(screen.queryByRole("button", { name: "Copy answer" })).not.toBeInTheDocument();
  });
});

describe("hostile model output", () => {
  it("renders HTML, Markdown and URLs in answers and titles as inert text", async () => {
    await answer("hostile");
    const [article] = articles();
    expect(article.querySelector("script, img, b, a[href^='javascript']")).toBeNull();
    expect(window.__xss).toBeUndefined();
    expect(within(article).getByText(/<script>window.__xss=1<\/script>/)).toBeInTheDocument();
    expect(within(article).getByText(/\[click\]\(javascript:window.__xss=3\)/)).toBeInTheDocument();
    expect(within(article).getByText("Source: <b>bold source</b>")).toBeInTheDocument();
    expect(within(article).queryByRole("link", { name: /evil\.example/ })).not.toBeInTheDocument();
  });

  it("never turns URLs in answer text into links", async () => {
    await answer("malformed");
    expect(screen.getByText(/https:\/\/evil\.example\/phish javascript:alert\(1\)/)).toBeInTheDocument();
    expect(document.querySelector('a[href*="evil.example"]')).toBeNull();
  });
});

describe("grouped evidence (replayed real P4-R03 response)", () => {
  it("shows one card for E4 and E9 and keeps every id visible", async () => {
    await answer(replayedFixtures["replayed-p4-r03"]);
    const cards = document.querySelectorAll(".assistant-evidence-card");
    expect(cards).toHaveLength(3);
    expect(screen.getByRole("button", { name: /Cited evidence \(3\)/ })).toBeInTheDocument();
    const grouped = document.getElementById("assistant-exchange-1-evidence-E4");
    expect(within(grouped).getByText("E4, E9")).toBeInTheDocument();
    expect(within(grouped).getByText(/Cited as E4 and E9: the same record was returned more than once\./)).toBeInTheDocument();
    expect(document.getElementById("assistant-exchange-1-evidence-E9")).toBeNull();
  });

  it.each(["E1", "E2", "E4", "E9"])("citation %s focuses its (grouped) card", async (id) => {
    const { user } = await answer(replayedFixtures["replayed-p4-r03"]);
    const button = within(articles()[0]).getByRole("button", { name: new RegExp(`^Evidence ${id}:`) });
    const target = id === "E9" ? "E4" : id;
    expect(button).toHaveAttribute("aria-controls", `assistant-exchange-1-evidence-${target}`);
    await user.click(evidenceToggle(articles()[0]));
    await user.click(button);
    expect(document.getElementById(`assistant-exchange-1-evidence-${target}`)).toHaveFocus();
  });

  it("keeps grouped targets separate across exchanges with overlapping ids", async () => {
    const { user, ask } = await answer(replayedFixtures["replayed-p4-r03"]);
    await ask("Again");
    server.last.respond(200, replayedFixtures["replayed-p4-r03"]);
    await waitFor(() => expect(screen.getAllByRole("button", { name: "Copy answer" })).toHaveLength(2));
    const ids = [...document.querySelectorAll("[id]")].map((el) => el.id);
    expect(new Set(ids).size).toBe(ids.length);
    const e9 = within(articles()[1]).getByRole("button", { name: /^Evidence E9:/ });
    expect(e9).toHaveAttribute("aria-controls", "assistant-exchange-2-evidence-E4");
    await user.click(e9);
    expect(document.getElementById("assistant-exchange-2-evidence-E4")).toHaveFocus();
  });

  it("does not change the answer text, citation buttons or tool activity", async () => {
    const { user } = await answer(replayedFixtures["replayed-p4-r03"]);
    expect(within(articles()[0]).getAllByRole("button", { name: /^Evidence E/ }).map((b) => b.textContent)).toEqual(["E1", "E2", "E4", "E9"]);
    await user.click(toolsToggle());
    expect(document.querySelectorAll(".assistant-tool")).toHaveLength(3);
  });
});

describe("inline emphasis", () => {
  it("renders the real P4-R09 **not** as bold text and copies the original answer", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    await answer(replayedFixtures["replayed-p4-r09"], "Why did Einstein win the Nobel Prize for relativity?");
    const answerText = document.querySelector(".assistant-answer-text");
    const strong = answerText.querySelector("strong");
    expect(strong).toHaveTextContent(/^not$/);
    expect(answerText.textContent).not.toContain("**");
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText } });
    fireEvent.click(screen.getByRole("button", { name: "Copy answer" }));
    await screen.findByText("Answer copied");
    expect(writeText).toHaveBeenCalledWith(replayedFixtures["replayed-p4-r09"].answer);
    expect(writeText.mock.calls[0][0]).toContain("**not**");
  });

  it("keeps citations interactive inside and next to emphasis", async () => {
    const { user } = await answer({ ...fixtures["real-r04"], answer: "**Drew Weissman [E1]**[E2] and **[E3]** won." });
    const strongs = document.querySelectorAll(".assistant-answer-text strong");
    expect(strongs).toHaveLength(2);
    const inside = within(strongs[0]).getByRole("button", { name: "Evidence E1: Drew Weissman" });
    await user.click(inside);
    expect(document.getElementById("assistant-exchange-1-evidence-E1")).toHaveFocus();
    expect(within(strongs[1]).getByRole("button", { name: /^Evidence E3:/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Evidence E2:/ }).closest("strong")).toBeNull();
  });

  it("leaves malformed emphasis literal", async () => {
    await answer({ ...fixtures["real-r04"], answer: "An ** unmatched marker and **across\nlines** stay [E1]." });
    const answerText = document.querySelector(".assistant-answer-text");
    expect(answerText.querySelector("strong")).toBeNull();
    expect(answerText.textContent).toBe("An ** unmatched marker and **across\nlines** stay E1.");
  });

  it("escapes hostile HTML inside emphasis", async () => {
    await answer({ ...fixtures["real-r04"], answer: '**<img src=x onerror="window.__xss=9"><script>window.__xss=8</script>** [E1]' });
    const strong = document.querySelector(".assistant-answer-text strong");
    expect(strong.querySelector("img, script")).toBeNull();
    expect(strong.textContent).toBe('<img src=x onerror="window.__xss=9"><script>window.__xss=8</script>');
    expect(window.__xss).toBeUndefined();
  });
});
