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

async function answer(fixture, question = "Who won the 2023 Medicine prize and what did they discover?", options = {}) {
  const page = renderAssistant(options);
  await page.ask(question);
  server.last.respond(200, typeof fixture === "string" ? fixtures[fixture] : fixture);
  await screen.findByRole("button", { name: "Copy answer" }).catch(() => {});
  return page;
}

const articles = () => screen.getAllByRole("article");
const answerText = (index = 0) => document.querySelectorAll(".assistant-answer-text")[index];
const coverageAbstention = {
  ...fixtures["real-r06"],
  answer: "Nobel Explorer’s database only covers prizes awarded through 2025, so it has no information on who won the 2026 Chemistry Prize.",
};
const evidenceToggle = (scope = document.body) => within(scope).getByRole("button", { name: /^Sources \(\d+\)/ });
// The hidden attribute is what the component controls. Whether CSS honours it
// (the Phase 4C bug) is covered by styles/assistantStyles.test.js and the
// real-browser checks, because jsdom always treats [hidden] as display: none.
const isRendered = (element) => !element.hidden;
const toolsToggle = (scope = document.body) => within(scope).getByRole("button", { name: "How this answer was found" });

describe("evidence cards and provenance", () => {
  it("keeps Sources collapsed by default and shows no tool activity publicly", async () => {
    await answer("real-r04");
    expect(evidenceToggle()).toHaveAttribute("aria-expanded", "false");
    expect(isRendered(document.getElementById("assistant-exchange-1-evidence-list"))).toBe(false);
    expect(screen.queryByRole("button", { name: "How this answer was found" })).not.toBeInTheDocument();
    expect(document.getElementById("assistant-exchange-1-tools-panel")).toBeNull();
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });

  it("renders database records with source and an internal profile link that opens in a new tab", async () => {
    const { user } = await answer("real-r04");
    await user.click(evidenceToggle());
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
    const { user } = await answer("real-r04");
    await user.click(evidenceToggle());
    const card = document.getElementById("assistant-exchange-1-evidence-E3");
    expect(within(card).getByText("Linked source")).toBeInTheDocument();
    const link = within(card).getByRole("link", { name: /The Nobel Prize in Physiology or Medicine 2023 – Summary \(opens in a new tab\)/ });
    expect(link).toHaveAttribute("href", "https://www.nobelprize.org/prizes/medicine/2023/summary/");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
    expect(card.textContent).not.toMatch(/verified/i);
  });

  it("labels educational content as unverified and shows the related source as text only", async () => {
    const { user } = await answer("real-r03", "Explain click chemistry in simple terms.");
    await user.click(evidenceToggle());
    const card = document.getElementById("assistant-exchange-1-evidence-E1");
    expect(within(card).getByText("Educational explanation")).toBeInTheDocument();
    expect(within(card).getByText("Nobel Explorer teaching content; no stored external citation")).toBeInTheDocument();
    expect(card.querySelector(".assistant-evidence-warning")).toBeNull(); // neutral, not a yellow warning
    expect(card.textContent).not.toMatch(/independently verified|verified source/i);
    expect(within(card).getByText("Related context: The Nobel Prize in Chemistry 2022 – Summary")).toBeInTheDocument();
    expect(within(card).queryByRole("link")).not.toBeInTheDocument();
    expect(document.body.innerHTML).not.toContain("nobelprize.org/prizes/chemistry");
  });

  it("handles unknown provenance and unsafe or malformed records without links or crashes", async () => {
    const { user } = await answer("malformed");
    await user.click(evidenceToggle());
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

describe("learner view: hidden evidence ids, sources with supported statements", () => {
  it("hides inline evidence ids and keeps punctuation tidy", async () => {
    await answer("real-r04");
    expect(answerText().textContent).toBe(
      "Katalin Karikó and Drew Weissman shared the 2023 Physiology or Medicine prize. They discovered that modifying "
      + "nucleosides in synthetic mRNA can reduce unwanted immune activation, helping cells translate the mRNA into protein "
      + "and enabling effective mRNA vaccines against COVID-19.",
    );
    expect(screen.queryByRole("button", { name: /^Evidence E/ })).not.toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/\bE\d+\b/);
  });

  it("lists, inside each source, the statements that source supports", async () => {
    const { user } = await answer("real-r04");
    await user.click(evidenceToggle());
    const weissman = within(document.getElementById("assistant-exchange-1-evidence-E1"));
    expect(weissman.getByText("Supports")).toBeInTheDocument();
    expect(weissman.getByText("Katalin Karikó and Drew Weissman shared the 2023 Physiology or Medicine prize.")).toBeInTheDocument();
    const contribution = within(document.getElementById("assistant-exchange-1-evidence-E3"));
    expect(contribution.getByText(/They discovered that modifying nucleosides in synthetic mRNA/)).toBeInTheDocument();
    expect(contribution.queryByText(/shared the 2023 Physiology or Medicine prize/)).not.toBeInTheDocument();
  });

  it("keeps validation markers visible as warnings", async () => {
    await answer("partial");
    expect(within(answerText()).getByText("[unverified]")).toBeInTheDocument();
    expect(within(answerText()).getByText("[link removed]")).toBeInTheDocument();
  });

  it("drops unknown evidence ids from the text without crashing", async () => {
    await answer({ ...fixtures["real-r04"], answer: "Unknown [E9] and known [E1]." });
    expect(answerText().textContent).toBe("Unknown and known.");
  });

  it("keeps the Sources panel and its ids separate across exchanges", async () => {
    const { ask } = await answer("real-r04");
    await ask("Second question");
    server.last.respond(200, fixtures["real-r04"]);
    await waitFor(() => expect(screen.getAllByRole("button", { name: "Copy answer" })).toHaveLength(2));
    const ids = [...document.querySelectorAll("[id]")].map((el) => el.id);
    expect(new Set(ids).size).toBe(ids.length);
    expect(evidenceToggle(articles()[1])).toHaveAttribute("aria-controls", "assistant-exchange-2-evidence-list");
  });
});

describe("grounding and limitations", () => {
  it.each([
    ["partial", "Some references could not be validated."],
    ["real-r09", "No evidence references provided."],
    [coverageAbstention, "No supporting evidence retrieved."],
  ])("%j keeps the meaningful warning %s", async (fixture, label) => {
    await answer(fixture);
    const notes = within(screen.getByRole("region", { name: "Limitations" }));
    expect(notes.getByText(label)).toBeInTheDocument();
  });

  it("does not repeat a limitation that only restates the grounding warning", async () => {
    await answer(coverageAbstention);
    const notes = within(screen.getByRole("region", { name: "Limitations" }));
    expect(notes.getByText("No supporting evidence retrieved.")).toBeInTheDocument();
    expect(notes.queryByText("No supporting evidence was retrieved, so this answer is not based on Nobel Explorer data.")).not.toBeInTheDocument();
    expect(notes.getByText(/Laureate search did not complete/)).toBeInTheDocument();
  });

  it("shows no grounding badge for a fully cited answer and keeps the accuracy disclaimer inside collapsed Sources", async () => {
    const { user } = await answer("real-r04");
    expect(screen.queryByText(/Includes evidence references/)).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Limitations" })).not.toBeInTheDocument();
    const disclaimer = screen.getByText(
      "AI-generated answers may contain errors. Citations indicate referenced information but do not guarantee factual correctness.",
    );
    expect(document.getElementById("assistant-exchange-1-evidence-list")).toContainElement(disclaimer);
    expect(document.querySelector(".assistant-composer")).not.toHaveTextContent(/may contain errors/);
    expect(evidenceToggle()).toHaveAttribute("aria-expanded", "false");
    await user.click(evidenceToggle());
    expect(screen.getByRole("region", { name: "Sources" })).toContainElement(disclaimer);
  });

  it("does not classify null or unknown grounding values", async () => {
    await answer({ ...fixtures["real-r04"], grounding: "mystery" });
    expect(screen.queryByRole("region", { name: "Limitations" })).not.toBeInTheDocument();
  });

  it("moves the educational-provenance notice into the collapsed Sources panel", async () => {
    const { user } = await answer("real-r03", "Explain click chemistry in simple terms.");
    const notice = screen.getByText(/Educational explanations are Nobel Explorer's own teaching content/);
    expect(document.getElementById("assistant-exchange-1-evidence-list")).toContainElement(notice);
    expect(screen.queryByRole("region", { name: "Limitations" })).not.toBeInTheDocument();
    await user.click(evidenceToggle());
    expect(notice).toBeVisible();
    expect(screen.getByText("Educational explanation")).toBeVisible();
  });

  it("keeps the notice under the answer when there is no Sources panel to hold it", async () => {
    await answer({ ...fixtures["real-r03"], citations: [] });
    const notes = within(screen.getByRole("region", { name: "Limitations" }));
    expect(notes.getByText(/Educational explanations are Nobel Explorer's own teaching content/)).toBeInTheDocument();
  });

  it("presents a correct abstention (no evidence) without an error notice", async () => {
    await answer("real-r06", "Who won the Nobel Prize in Mathematics in 1950?");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.getByText(/There is no Nobel Prize in Mathematics/)).toBeInTheDocument();
  });

  it("shows friendly, de-duplicated limitations instead of technical messages", async () => {
    await answer(coverageAbstention);
    const limits = within(screen.getByRole("region", { name: "Limitations" }));
    expect(limits.getByText("Laureate search did not complete: the requested search parameters could not be processed.")).toBeInTheDocument();
    expect(limits.getByText("No supporting evidence retrieved.")).toBeInTheDocument();
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

describe("general scientific knowledge notes", () => {
  const NOTE = "General scientific knowledge · No retrieved source";
  const generalAnswer = {
    ...fixtures["real-r09"],
    answer: "Sourdough rises because wild yeasts and lactic acid bacteria ferment sugars in the flour, producing carbon dioxide and acids that give the bread its texture and sour taste.",
  };

  it("marks an uncited science answer as general knowledge and hides the redundant no-match lines", async () => {
    await answer(generalAnswer, "Explain sourdough fermentation.");
    const notes = within(screen.getByRole("region", { name: "Limitations" }));
    expect(notes.getByText(NOTE)).toBeInTheDocument();
    expect(notes.queryByText(/No evidence references provided/)).not.toBeInTheDocument();
    expect(notes.queryByText(/may not closely match this question/)).not.toBeInTheDocument();
    expect(notes.queryByText(/does not reference any of the evidence/)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^Evidence E/ })).not.toBeInTheDocument();
    expect(screen.getByText("ⓘ")).toHaveAttribute("aria-hidden", "true");
  });

  it("treats a no-evidence correction as general knowledge but keeps real tool problems", async () => {
    await answer("real-r06", "Who won the Nobel Prize in Mathematics in 1950?");
    const notes = within(screen.getByRole("region", { name: "Limitations" }));
    expect(notes.getByText(NOTE)).toBeInTheDocument();
    expect(notes.getByText(/Laureate search did not complete/)).toBeInTheDocument();
    expect(notes.queryByText("No supporting evidence retrieved.")).not.toBeInTheDocument();
  });

  it("keeps the normal warnings for abstentions instead of the general-knowledge note", async () => {
    await answer("real-r09", "Explain sourdough fermentation."); // "no reliable evidence" abstention
    const notes = within(screen.getByRole("region", { name: "Limitations" }));
    expect(notes.queryByText(NOTE)).not.toBeInTheDocument();
    expect(notes.getByText("No evidence references provided.")).toBeInTheDocument();
  });

  it("keeps the no-evidence warning for a coverage abstention", async () => {
    await answer(coverageAbstention, "Who won the 2026 Chemistry prize?");
    const notes = within(screen.getByRole("region", { name: "Limitations" }));
    expect(notes.queryByText(NOTE)).not.toBeInTheDocument();
    expect(notes.getByText("No supporting evidence retrieved.")).toBeInTheDocument();
  });

  it("labels a cited answer with an uncited general paragraph as mixed", async () => {
    await answer({
      ...fixtures["real-r04"],
      answer: "Katalin Karikó and Drew Weissman shared the 2023 prize [E1][E2].\n\nIn general, vaccines train the immune system to recognise a pathogen without causing the disease itself.",
    });
    const notes = within(screen.getByRole("region", { name: "Limitations" }));
    expect(notes.getByText("Partly sourced · Some statements use general scientific knowledge")).toBeInTheDocument();
    expect(evidenceToggle()).toBeInTheDocument(); // the sourced part is still backed by Sources
  });

  it("shows no knowledge note for a fully cited answer", async () => {
    await answer("real-r04");
    expect(screen.queryByText(/General scientific knowledge|Partly sourced/)).not.toBeInTheDocument();
  });
});

describe("tool activity (debug only)", () => {
  it("is not shown on the public page", async () => {
    await answer("real-r04");
    expect(screen.queryByText(/Search Nobel laureates/)).not.toBeInTheDocument();
  });

  it("is available with ?debug, collapsed by default, with friendly allow-listed details", async () => {
    const { user } = await answer("real-r04", undefined, { path: "/assistant?debug" });
    const toggle = toolsToggle();
    const panel = document.getElementById("assistant-exchange-1-tools-panel");
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(isRendered(panel)).toBe(false);
    await user.click(toggle);
    expect(isRendered(panel)).toBe(true);
    const details = within(panel);
    expect(details.getByText("Search Nobel laureates")).toBeInTheDocument();
    expect(details.getByText("Physiology or Medicine")).toBeInTheDocument();
    expect(panel.textContent).not.toMatch(/call_|req-|latency|9572|gpt-6|\{/);
  });

  it("never shows ids, credentials or raw error types even in debug mode", async () => {
    const { user } = await answer("malformed", undefined, { path: "/assistant?debug" });
    await user.click(toolsToggle());
    const text = document.getElementById("assistant-exchange-1-tools-panel").textContent;
    expect(text).toContain("Unrecognized tool");
    expect(text).not.toMatch(/FAKE-CREDENTIAL|HIDDEN_EXTRA|call_internal|rm_rf_tool|UNKNOWN TOOL QUERY|DROP TABLE|internal_error|unknown_tool/);
  });
});

describe("copy answer", () => {
  function stubClipboard(writeText) {
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText } });
  }

  it("is a small icon button with an accessible name", async () => {
    await answer("real-r04");
    const button = screen.getByRole("button", { name: "Copy answer" });
    expect(button).toHaveClass("assistant-icon-button");
    expect(button.textContent).toBe("");
    expect(button.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
  });

  it("copies the answer as learners see it (no evidence ids) and confirms only after success", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    await answer("real-r04");
    stubClipboard(writeText);
    fireEvent.click(screen.getByRole("button", { name: "Copy answer" }));
    expect(await screen.findByText("Copied")).toHaveAttribute("role", "status");
    expect(writeText).toHaveBeenCalledWith(answerText().textContent);
    expect(writeText.mock.calls[0][0]).not.toMatch(/\[E\d/);
  });

  it("reports a clipboard rejection without claiming success", async () => {
    await answer("real-r04");
    stubClipboard(vi.fn().mockRejectedValue(new DOMException("denied", "NotAllowedError")));
    fireEvent.click(screen.getByRole("button", { name: "Copy answer" }));
    expect(await screen.findByText("Could not copy. Select the answer text to copy it manually.")).toBeInTheDocument();
    expect(screen.queryByText("Copied")).not.toBeInTheDocument();
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
    expect(screen.getByText("Copied")).toBeInTheDocument();
    await act(async () => vi.advanceTimersByTime(2500));
    expect(screen.queryByText("Copied")).not.toBeInTheDocument();

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
    expect(answerText()).toHaveTextContent(/<script>window.__xss=1<\/script>/);
    expect(answerText()).toHaveTextContent(/\[click\]\(javascript:window.__xss=3\)/);
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
  it("shows one source for E4 and E9 with the statement it supports, without showing ids", async () => {
    const { user } = await answer(replayedFixtures["replayed-p4-r03"]);
    expect(screen.getByRole("button", { name: /^Sources \(3\)/ })).toBeInTheDocument();
    await user.click(evidenceToggle());
    expect(document.querySelectorAll(".assistant-evidence-card")).toHaveLength(3);
    const grouped = within(document.getElementById("assistant-exchange-1-evidence-E4"));
    expect(grouped.getByText("Nucleoside Base Modifications and mRNA Vaccines")).toBeInTheDocument();
    expect(grouped.getAllByText(/They discovered that modifying nucleosides/)).toHaveLength(1);
    expect(document.getElementById("assistant-exchange-1-evidence-E9")).toBeNull();
    expect(screen.getByRole("region", { name: "Sources" }).textContent).not.toMatch(/\bE\d+\b/);
  });

  it("does not change the answer text", async () => {
    await answer(replayedFixtures["replayed-p4-r03"]);
    expect(answerText().textContent).toBe(
      "The 2023 Nobel Prize in Physiology or Medicine was shared by Katalin Karikó and Drew Weissman. They discovered "
      + "that modifying nucleosides in synthetic mRNA reduces unwanted immune activation, helping make effective mRNA "
      + "vaccines against COVID-19 possible.",
    );
  });
});

describe("inline emphasis", () => {
  it("renders the real P4-R09 **not** as bold text and copies clean text", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    await answer(replayedFixtures["replayed-p4-r09"], "Why did Einstein win the Nobel Prize for relativity?");
    const strong = answerText().querySelector("strong");
    expect(strong).toHaveTextContent(/^not$/);
    expect(answerText().textContent).not.toContain("**");
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText } });
    fireEvent.click(screen.getByRole("button", { name: "Copy answer" }));
    await screen.findByText("Copied");
    expect(writeText.mock.calls[0][0]).toMatch(/^Einstein did not receive the Nobel Prize for relativity\./);
  });

  it("keeps emphasis when citations inside it are hidden", async () => {
    await answer({ ...fixtures["real-r04"], answer: "**Drew Weissman [E1]**[E2] and **[E3] Karikó** won." });
    const strongs = answerText().querySelectorAll("strong");
    expect([...strongs].map((el) => el.textContent)).toEqual(["Drew Weissman", "Karikó"]);
    expect(answerText().textContent).toBe("Drew Weissman and Karikó won.");
  });

  it("leaves malformed emphasis literal", async () => {
    await answer({ ...fixtures["real-r04"], answer: "An ** unmatched marker and **across\nlines** stay [E1]." });
    expect(answerText().querySelector("strong")).toBeNull();
    expect(answerText().textContent).toBe("An ** unmatched marker and **across\nlines** stay.");
  });

  it("escapes hostile HTML inside emphasis", async () => {
    await answer({ ...fixtures["real-r04"], answer: '**<img src=x onerror="window.__xss=9"><script>window.__xss=8</script>** [E1]' });
    const strong = document.querySelector(".assistant-answer-text strong");
    expect(strong.querySelector("img, script")).toBeNull();
    expect(strong.textContent).toBe('<img src=x onerror="window.__xss=9"><script>window.__xss=8</script>');
    expect(window.__xss).toBeUndefined();
  });
});
