import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import EducationalEmptyState from "../components/laureates/EducationalEmptyState";
import { getLearnTopics } from "../services/api";
import { formatNameList } from "../utils/nameList";

const levels = ["Simple", "Explore", "Advanced", "Expert"];

const contributionTypeLabels = {
  NOBEL_LINKED: "Nobel-Linked",
  BEYOND_NOBEL: "Beyond Nobel",
};

const categoryIcons = {
  Physics: "⚛️",
  Chemistry: "🧪",
  "Physiology or Medicine": "❤️",
  Literature: "📖",
  Peace: "🕊️",
  "Economic Sciences": "📊",
};

function getTopicIcon(topic) {
  if (topic.contribution_type === "NOBEL_LINKED" && topic.category) {
    return categoryIcons[topic.category] || "✦";
  }
  return "🌌";
}

function getInitials(name) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

function LessonAvatar({ imageUrl, name }) {
  if (imageUrl) {
    return <img className="learn-lesson-avatar" src={imageUrl} alt={name} loading="lazy" />;
  }

  return (
    <span className="learn-lesson-avatar learn-lesson-avatar--placeholder" aria-hidden="true">
      {getInitials(name)}
    </span>
  );
}

function LevelPicker({ selected, onSelect }) {
  return (
    <div className="learn-level-picker" role="group" aria-label="Preferred learning level">
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

function LessonCard({ topic, preferredLevel }) {
  const awardLine =
    topic.contribution_type === "NOBEL_LINKED" && topic.category && topic.prize_year
      ? `${topic.category} • Nobel Prize ${topic.prize_year}`
      : "Beyond the Nobel Prize";

  const credits = topic.credited_laureates ?? [];
  const names = credits.length ? formatNameList(credits.map((credit) => credit.name)) : topic.laureate_name;
  const firstCredit = credits[0];
  const lessonHref = `/laureates/${firstCredit?.laureate_id ?? topic.laureate_id}?contribution=${topic.contribution_id}&section=learn&level=${preferredLevel}`;

  return (
    <article className="learn-lesson-card">
      <div className="learn-lesson-topic">
        <span className="learn-lesson-icon" aria-hidden="true">{getTopicIcon(topic)}</span>
        <div className="learn-lesson-topic-copy">
          <h3>{topic.title}</h3>
          <span className={`learn-lesson-type learn-lesson-type--${topic.contribution_type.toLowerCase()}`}>
            {contributionTypeLabels[topic.contribution_type]}
          </span>
        </div>
      </div>

      <div className="learn-lesson-byline">
        <LessonAvatar imageUrl={firstCredit ? firstCredit.image_url : topic.image_url} name={firstCredit?.name ?? topic.laureate_name} />
        <span>
          {names}
          <small>{awardLine}</small>
        </span>
      </div>

      {topic.summary && <p className="learn-lesson-summary">{topic.summary}</p>}

      <div className="learn-lesson-ctas">
        <Link className="learn-lesson-cta" to={lessonHref}>
          Start at {preferredLevel} Level <span aria-hidden="true">→</span>
        </Link>

        {topic.quiz_available && (
          <Link
            className="learn-quiz-badge learn-quiz-badge--link"
            to={`/quiz?contribution=${topic.contribution_id}&level=${preferredLevel}`}
          >
            <span aria-hidden="true">✓</span> Take the Quiz <span aria-hidden="true">→</span>
          </Link>
        )}
      </div>
    </article>
  );
}

function LearnPage() {
  const [topics, setTopics] = useState([]);
  const [status, setStatus] = useState("loading");
  const [preferredLevel, setPreferredLevel] = useState("Simple");

  useEffect(() => {
    const controller = new AbortController();
    setStatus("loading");

    getLearnTopics({ signal: controller.signal })
      .then((data) => {
        setTopics(data);
        setStatus("success");
      })
      .catch((error) => {
        if (error.name !== "AbortError") setStatus("error");
      });

    return () => controller.abort();
  }, []);

  return (
    <div className="learn-page">
      <div className="container">
        <div className="learn-heading">
          <p className="eyebrow">Learn</p>
          <h1>Learn Nobel-winning science at your level.</h1>
          <p className="learn-subtitle">
            Discover the ideas behind Nobel Prizes, from the everyday version to the technical detail.
          </p>
        </div>

        <div className="learn-level-section">
          <p className="learn-level-label">Choose your learning level</p>
          <LevelPicker selected={preferredLevel} onSelect={setPreferredLevel} />
        </div>

        {status === "loading" && (
          <p className="learn-status" role="status">Loading available lessons…</p>
        )}

        {status === "error" && (
          <EducationalEmptyState title="Lessons unavailable">
            We couldn’t load the available lessons right now. Please try again shortly.
          </EducationalEmptyState>
        )}

        {status === "success" && topics.length === 0 && (
          <EducationalEmptyState title="Lessons coming soon">
            Educational lessons have not been added yet. Check back soon.
          </EducationalEmptyState>
        )}

        {status === "success" && topics.length > 0 && (
          <div className="learn-lesson-grid">
            {topics.map((topic) => (
              <LessonCard topic={topic} preferredLevel={preferredLevel} key={topic.contribution_id} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default LearnPage;
