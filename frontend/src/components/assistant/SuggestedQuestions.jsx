// Suggestions fill the input; they never send a request by themselves.
function SuggestedQuestions({ questions, onSelect }) {
  return (
    <section className="assistant-suggestions" aria-labelledby="assistant-suggestions-heading">
      <h2 className="visually-hidden" id="assistant-suggestions-heading">Try a question</h2>
      <ul>
        {questions.map((question) => (
          <li key={question}>
            <button type="button" className="assistant-suggestion" onClick={() => onSelect(question)}>
              {question}
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}

export default SuggestedQuestions;
