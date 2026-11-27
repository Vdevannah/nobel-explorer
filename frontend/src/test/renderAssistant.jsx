import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import AssistantPage from "../pages/AssistantPage";

// Renders the assistant page. jsdom cannot evaluate the CSS cascade for
// [hidden] (see assistantStyles.test.js); real rendering is checked in Chrome.
//
// Under fake timers use askNow(): user-event goes through Testing Library's
// async wrapper, which waits on a real setTimeout and only advances fake
// timers when a global "jest" exists, so it would hang under Vitest.
export function renderAssistant() {
  const user = userEvent.setup();
  const view = render(
    <MemoryRouter>
      <AssistantPage />
    </MemoryRouter>,
  );
  const textarea = () => screen.getByLabelText("Your question");
  const askButton = () => screen.getByRole("button", { name: /^(Ask|Asking…)$/ });
  async function ask(question) {
    await user.clear(textarea());
    await user.type(textarea(), question);
    await user.click(askButton());
  }
  function askNow(question) {
    fireEvent.change(textarea(), { target: { value: question } });
    fireEvent.click(askButton());
  }
  return {
    ...view,
    askNow,
    user,
    textarea,
    askButton,
    ask,
    // Queries scoped to the visible conversation (the hidden announcer repeats some text).
    conversation: () => within(screen.getByRole("region", { name: "Questions and answers in this session" })),
    announcer: () => document.querySelector('[aria-live="polite"]'),
  };
}
