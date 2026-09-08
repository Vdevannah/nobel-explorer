import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import EducationalEmptyState from "../components/laureates/EducationalEmptyState";
import { checkQuizAnswer, getContributionQuiz, getLearnTopics } from "../services/api";

const levels = ["Simple", "Explore", "Advanced", "Expert"];
const choiceLetters = ["A", "B", "C", "D"];

const contributionTypeLabels = {
  NOBEL_LINKED: "Nobel-Linked",
  BEYOND_NOBEL: "Beyond Nobel",
};

function updateSearchParams(setSearchParams, updates) {
  setSearchParams(
    (previous) => {
      const next = new URLSearchParams(previous);
      Object.entries(updates).forEach(([key, value]) => {
        if (value === null || value === undefined) {
          next.delete(key);
        } else {
          next.set(key, String(value));
        }
      });
      return next;
    },
    { replace: true },
  );
}

function ContributionPicker({ topics, selectedId, onSelect }) {
  return (
    <div className="quiz-contribution-picker" role="group" aria-label="Choose a contribution to quiz on">
      {topics.map((topic) => {
        const selected = topic.contribution_id === selectedId;
        return (
          <button
            className={`quiz-contribution-option${selected ? " quiz-contribution-option--active" : ""}`}
            type="button"
            aria-pressed={selected}
            onClick={() => onSelect(topic.contribution_id)}
            key={topic.contribution_id}
          >
            <span className="quiz-contribution-option-copy">
              <strong>{topic.title}</strong>
              <small>{topic.laureate_name}</small>
            </span>
            <span className={`learn-lesson-type learn-lesson-type--${topic.contribution_type.toLowerCase()}`}>
              {contributionTypeLabels[topic.contribution_type]}
            </span>
          </button>
        );
      })}
    </div>
  );
}

function LevelPicker({ selected, onSelect }) {
  return (
    <div className="learn-level-picker" role="group" aria-label="Choose a learning level">
      {levels.map((level) => (
        <button
          className={`learn-level-button${level === selected ? " learn-level-button--active" : ""} learn-level-button--${level.toLowerCase()}`}
          type="button"
          aria-pressed={level === selected}
          onClick={() => onSelect(level)}
          key={level}
        >
          {level}
        </button>
      ))}
    </div>
  );
}

function QuizSetup({
  topics,
  topicsStatus,
  selectedContributionId,
  selectedLevel,
  onSelectContribution,
  onSelectLevel,
  onStart,
}) {
  return (
    <div className="quiz-setup">
      <div className="quiz-heading">
        <p className="eyebrow">Quiz</p>
        <h1>Test your knowledge</h1>
        <p className="quiz-subtitle">
          Choose a contribution and a learning level, then start a short quiz.
        </p>
      </div>

      {topicsStatus === "loading" && (
        <p className="learn-status" role="status">Loading available quizzes…</p>
      )}

      {topicsStatus === "error" && (
        <EducationalEmptyState title="Quizzes unavailable">
          We couldn’t load available quizzes right now. Please try again shortly.
        </EducationalEmptyState>
      )}

      {topicsStatus === "success" && topics.length === 0 && (
        <EducationalEmptyState title="No quizzes yet">
          No contributions currently have quiz questions. Check back soon.
        </EducationalEmptyState>
      )}

      {topicsStatus === "success" && topics.length > 0 && (
        <>
          <div className="quiz-setup-section">
            <p className="learn-level-label">Choose a contribution</p>
            <ContributionPicker
              topics={topics}
              selectedId={selectedContributionId}
              onSelect={onSelectContribution}
            />
          </div>

          <div className="quiz-setup-section">
            <p className="learn-level-label">Choose your learning level</p>
            <LevelPicker selected={selectedLevel} onSelect={onSelectLevel} />
          </div>

          <button
            className="button button-primary quiz-start-button"
            type="button"
            disabled={!selectedContributionId}
            onClick={onStart}
          >
            Start Quiz <span aria-hidden="true">→</span>
          </button>
        </>
      )}
    </div>
  );
}

function QuestionCard({
  topic,
  level,
  question,
  index,
  total,
  selectedAnswer,
  submitted,
  feedback,
  feedbackStatus,
  onSelectAnswer,
  onSubmit,
  onNext,
  feedbackRef,
}) {
  return (
    <div className="quiz-session">
      <div className="quiz-session-header">
        <p className="eyebrow">{topic.title}</p>
        <p className="quiz-progress">{level} Level — Question {index + 1} of {total}</p>
        <div className="quiz-progress-dots" aria-hidden="true">
          {Array.from({ length: total }).map((_, dotIndex) => (
            <span
              className={`quiz-progress-dot${
                dotIndex === index
                  ? " quiz-progress-dot--current"
                  : dotIndex < index
                    ? " quiz-progress-dot--complete"
                    : ""
              }`}
              key={dotIndex}
            />
          ))}
        </div>
      </div>

      <div className="quiz-question-card">
        <h2 className="quiz-question-text">{question.question}</h2>

        <div className="quiz-choices" role="group" aria-label={`Answer choices for question ${index + 1}`}>
          {choiceLetters.map((letter) => {
            const choiceText = question[`choice_${letter.toLowerCase()}`];
            const isSelected = selectedAnswer === letter;
            const isCorrectChoice = submitted && feedback && letter === feedback.correct_answer;
            const isWrongSelection = submitted && isSelected && feedback && !feedback.correct;
            const stateClass = isCorrectChoice
              ? " quiz-choice--correct"
              : isWrongSelection
                ? " quiz-choice--incorrect"
                : isSelected
                  ? " quiz-choice--selected"
                  : "";
            return (
              <button
                className={`quiz-choice${stateClass}`}
                type="button"
                aria-pressed={isSelected}
                disabled={submitted}
                onClick={() => onSelectAnswer(letter)}
                key={letter}
              >
                <span className="quiz-choice-letter" aria-hidden="true">{letter}</span>
                <span className="quiz-choice-text">{choiceText}</span>
                {isCorrectChoice && <span className="quiz-choice-mark" aria-hidden="true">✓</span>}
                {isWrongSelection && <span className="quiz-choice-mark" aria-hidden="true">✗</span>}
              </button>
            );
          })}
        </div>

        {!submitted && (
          <button
            className="button button-primary quiz-submit-button"
            type="button"
            disabled={!selectedAnswer || feedbackStatus === "loading"}
            onClick={onSubmit}
          >
            {feedbackStatus === "loading" ? "Checking…" : "Submit Answer"}
          </button>
        )}

        {feedbackStatus === "error" && (
          <p className="quiz-feedback-error" role="alert">
            We couldn’t check that answer. Please try again.
          </p>
        )}

        {submitted && feedback && (
          <div className="quiz-feedback" ref={feedbackRef} tabIndex={-1} aria-live="polite">
            <p className={`quiz-feedback-verdict${feedback.correct ? " quiz-feedback-verdict--correct" : " quiz-feedback-verdict--incorrect"}`}>
              <span aria-hidden="true">{feedback.correct ? "✓" : "✗"}</span>{" "}
              {feedback.correct ? "Correct" : "Not Quite"}
            </p>
            {!feedback.correct && (
              <p className="quiz-feedback-answer">Correct answer: {feedback.correct_answer}</p>
            )}
            {feedback.answer_explanation && (
              <p className="quiz-feedback-explanation">{feedback.answer_explanation}</p>
            )}
            <button className="button button-primary quiz-next-button" type="button" onClick={onNext}>
              {index + 1 < total ? "Next Question" : "See Results"} <span aria-hidden="true">→</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function ResultsScreen({ topic, level, score, total, answerReview, onTryAgain, resultsHeadingRef }) {
  const percentage = total > 0 ? Math.round((score / total) * 100) : 0;
  const message =
    percentage === 100
      ? "Perfect score!"
      : percentage >= 70
        ? "Well done!"
        : percentage >= 40
          ? "Good effort — review the explanations below."
          : "Keep practicing — review the explanations below.";

  return (
    <div className="quiz-results">
      <h1 ref={resultsHeadingRef} tabIndex={-1}>Quiz Complete</h1>

      <div className="quiz-summary-card">
        <p className="quiz-summary-topic">{topic.title}</p>
        <p className="quiz-summary-level">{level} Level</p>
        <p className="quiz-summary-score">{score} / {total}</p>
        <p className="quiz-summary-percentage">{percentage}%</p>
      </div>

      <p className="quiz-results-message">{message}</p>

      <div className="quiz-results-actions">
        <button className="button button-primary" type="button" onClick={onTryAgain}>
          Try Again
        </button>
        <Link className="button button-secondary" to="/learn">
          Back to Learn
        </Link>
      </div>

      {answerReview.length > 0 && (
        <ul className="quiz-review">
          {answerReview.map((entry, index) => (
            <li className={`quiz-review-item${entry.correct ? " quiz-review-item--correct" : " quiz-review-item--incorrect"}`} key={index}>
              <span className="quiz-review-status" aria-hidden="true">{entry.correct ? "✓" : "✗"}</span>
              <span className="quiz-review-copy">
                <strong>{entry.questionText}</strong>
                <small>
                  Your answer: {entry.selectedAnswer} — {entry.selectedAnswerText}
                </small>
                {!entry.correct && (
                  <small>
                    Correct answer: {entry.correctAnswer} — {entry.correctAnswerText}
                  </small>
                )}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function QuizPage() {
  const [searchParams, setSearchParams] = useSearchParams();

  const [topics, setTopics] = useState([]);
  const [topicsStatus, setTopicsStatus] = useState("loading");

  const [phase, setPhase] = useState("setup");
  const [selectedContributionId, setSelectedContributionId] = useState(null);
  const [selectedLevel, setSelectedLevel] = useState("Simple");

  const [questions, setQuestions] = useState([]);
  const [questionsStatus, setQuestionsStatus] = useState("idle");
  const [currentIndex, setCurrentIndex] = useState(0);
  const [selectedAnswer, setSelectedAnswer] = useState(null);
  const [submitted, setSubmitted] = useState(false);
  const [feedback, setFeedback] = useState(null);
  const [feedbackStatus, setFeedbackStatus] = useState("idle");
  const [score, setScore] = useState(0);
  const [answerReview, setAnswerReview] = useState([]);

  const feedbackRef = useRef(null);
  const resultsHeadingRef = useRef(null);

  useEffect(() => {
    const controller = new AbortController();
    setTopicsStatus("loading");
    getLearnTopics({ signal: controller.signal })
      .then((data) => {
        setTopics(data.filter((topic) => topic.quiz_available));
        setTopicsStatus("success");
      })
      .catch((error) => {
        if (error.name !== "AbortError") setTopicsStatus("error");
      });
    return () => controller.abort();
  }, []);

  function startQuiz(contributionId, level) {
    setPhase("quiz");
    setQuestionsStatus("loading");
    getContributionQuiz(contributionId, { level })
      .then((data) => {
        setQuestions(data);
        setCurrentIndex(0);
        setSelectedAnswer(null);
        setSubmitted(false);
        setFeedback(null);
        setFeedbackStatus("idle");
        setScore(0);
        setAnswerReview([]);
        setQuestionsStatus(data.length ? "success" : "empty");
      })
      .catch(() => setQuestionsStatus("error"));
  }

  // Once the quiz-enabled contributions have loaded, honor a deep link
  // (?contribution=&level=) exactly once. Invalid/missing values fall back
  // to the setup screen instead of crashing or leaving a broken state.
  useEffect(() => {
    if (topicsStatus !== "success") return;
    const requestedContribution = Number(searchParams.get("contribution"));
    const requestedLevel = searchParams.get("level");
    const matchingTopic = topics.find(
      (topic) => topic.contribution_id === requestedContribution,
    );
    if (!matchingTopic) return;

    setSelectedContributionId(matchingTopic.contribution_id);
    if (levels.includes(requestedLevel)) {
      setSelectedLevel(requestedLevel);
      startQuiz(matchingTopic.contribution_id, requestedLevel);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [topicsStatus]);

  useEffect(() => {
    if (submitted && feedbackRef.current) {
      feedbackRef.current.focus();
    }
  }, [submitted, currentIndex]);

  useEffect(() => {
    if (phase === "results" && resultsHeadingRef.current) {
      resultsHeadingRef.current.focus();
    }
  }, [phase]);

  function handleStartClick() {
    if (!selectedContributionId) return;
    updateSearchParams(setSearchParams, {
      contribution: selectedContributionId,
      level: selectedLevel,
    });
    startQuiz(selectedContributionId, selectedLevel);
  }

  function handleSubmit() {
    if (!selectedAnswer) return;
    const question = questions[currentIndex];
    setFeedbackStatus("loading");
    checkQuizAnswer(question.question_id, selectedAnswer)
      .then((result) => {
        setFeedback(result);
        setSubmitted(true);
        setFeedbackStatus("success");
        setScore((previous) => previous + (result.correct ? 1 : 0));
        setAnswerReview((previous) => [
          ...previous,
          {
            questionText: question.question,
            selectedAnswer,
            selectedAnswerText: question[`choice_${selectedAnswer.toLowerCase()}`],
            correctAnswer: result.correct_answer,
            correctAnswerText: question[`choice_${result.correct_answer.toLowerCase()}`],
            correct: result.correct,
          },
        ]);
      })
      .catch(() => setFeedbackStatus("error"));
  }

  function handleNext() {
    if (currentIndex + 1 < questions.length) {
      setCurrentIndex((previous) => previous + 1);
      setSelectedAnswer(null);
      setSubmitted(false);
      setFeedback(null);
      setFeedbackStatus("idle");
    } else {
      setPhase("results");
    }
  }

  function handleTryAgain() {
    setCurrentIndex(0);
    setSelectedAnswer(null);
    setSubmitted(false);
    setFeedback(null);
    setFeedbackStatus("idle");
    setScore(0);
    setAnswerReview([]);
    setPhase("quiz");
  }

  const selectedTopic = topics.find((topic) => topic.contribution_id === selectedContributionId) || null;

  return (
    <div className="quiz-page">
      <div className="container">
        {phase === "setup" && (
          <QuizSetup
            topics={topics}
            topicsStatus={topicsStatus}
            selectedContributionId={selectedContributionId}
            selectedLevel={selectedLevel}
            onSelectContribution={setSelectedContributionId}
            onSelectLevel={setSelectedLevel}
            onStart={handleStartClick}
          />
        )}

        {phase === "quiz" && questionsStatus === "loading" && (
          <p className="learn-status" role="status">Loading quiz questions…</p>
        )}

        {phase === "quiz" && questionsStatus === "error" && (
          <EducationalEmptyState title="Quiz unavailable">
            We couldn’t load this quiz right now. Please try again shortly.
          </EducationalEmptyState>
        )}

        {phase === "quiz" && questionsStatus === "empty" && (
          <EducationalEmptyState title="No questions for this level">
            This contribution does not have quiz questions at the selected level yet.
          </EducationalEmptyState>
        )}

        {phase === "quiz" && questionsStatus === "success" && selectedTopic && (
          <QuestionCard
            topic={selectedTopic}
            level={selectedLevel}
            question={questions[currentIndex]}
            index={currentIndex}
            total={questions.length}
            selectedAnswer={selectedAnswer}
            submitted={submitted}
            feedback={feedback}
            feedbackStatus={feedbackStatus}
            onSelectAnswer={setSelectedAnswer}
            onSubmit={handleSubmit}
            onNext={handleNext}
            feedbackRef={feedbackRef}
          />
        )}

        {phase === "results" && selectedTopic && (
          <ResultsScreen
            topic={selectedTopic}
            level={selectedLevel}
            score={score}
            total={questions.length}
            answerReview={answerReview}
            onTryAgain={handleTryAgain}
            resultsHeadingRef={resultsHeadingRef}
          />
        )}
      </div>
    </div>
  );
}

export default QuizPage;
