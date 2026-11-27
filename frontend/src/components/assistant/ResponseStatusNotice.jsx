// Maps a request outcome to a visitor-facing notice. Provider and server
// diagnostics are never shown verbatim.
export function describeOutcome(exchange) {
  if (exchange.phase === "cancelled") {
    return {
      tone: "neutral",
      title: "Request cancelled",
      message: "Stopped waiting; the server may still finish this request.",
    };
  }

  const { result } = exchange;
  if (!result) return null;

  switch (result.kind) {
    case "unavailable":
      return {
        tone: "warning",
        title: "The AI assistant is currently unavailable",
        message: "It may be disabled or not configured on this server. The rest of Nobel Explorer still works.",
      };
    case "validation_error":
      return { tone: "error", title: "The question could not be accepted", message: result.message };
    case "network_error":
      return {
        tone: "error",
        title: "Could not reach the Nobel Explorer server",
        message: "Check your connection or try again in a moment.",
      };
    case "malformed_response":
    case "unexpected_response":
      return {
        tone: "error",
        title: "Unexpected response",
        message: "The server returned a response the assistant could not read. Please try again.",
      };
    case "aborted":
      return null;
    default:
      break;
  }

  const { status, error } = result.response;
  if (status === "unavailable") {
    return {
      tone: "warning",
      title: "The AI assistant is currently unavailable",
      message: "It may be disabled or not configured on this server. The rest of Nobel Explorer still works.",
    };
  }
  if (status === "budget_exhausted") {
    return {
      tone: "warning",
      title: "The assistant reached its processing limit",
      message: "It stopped before finishing. Any partial answer and limitations are shown below. Try a narrower question.",
    };
  }
  if (status === "timeout") {
    return {
      tone: "warning",
      title: "The assistant ran out of time",
      message: "It stopped before finishing. Any partial answer and limitations are shown below. Try a narrower question.",
    };
  }
  if (status === "error") {
    const providerProblem = typeof error?.type === "string" && error.type.startsWith("provider_");
    return {
      tone: "error",
      title: providerProblem ? "The language model service had a problem" : "Something went wrong",
      message: providerProblem
        ? "The AI service could not complete this request. Please try again later."
        : "The assistant could not answer this question. Please try again.",
    };
  }
  return null;
}

function ResponseStatusNotice({ exchange }) {
  const notice = describeOutcome(exchange);
  if (!notice) return null;

  return (
    <div
      className={`assistant-notice assistant-notice--${notice.tone}`}
      role={notice.tone === "error" ? "alert" : "status"}
    >
      <p className="assistant-notice-title">{notice.title}</p>
      <p>{notice.message}</p>
    </div>
  );
}

export default ResponseStatusNotice;
