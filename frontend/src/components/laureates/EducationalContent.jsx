import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { getContributionById, getContributionQuiz } from "../../services/api";
import { getConnectionVisual, getContributionVisual } from "../../data/educationalVisuals";
import EducationalEmptyState from "./EducationalEmptyState";
import EducationalVisual from "./EducationalVisual";

const levels = ["Simple", "Explore", "Advanced", "Expert"];
const educationSections = [
  { id: "explore", label: "Explore" },
  { id: "learn", label: "Learn" },
  { id: "impact", label: "Impact" },
  { id: "applications", label: "Applications" },
  { id: "quiz", label: "Quiz" },
];

const levelDetails = {
  Simple: { audience: "Grades 4–6", style: "Everyday language, minimal math", icon: "👧" },
  Explore: { audience: "Grades 7–9", style: "Build vocabulary and understanding", icon: "👦" },
  Advanced: { audience: "Grades 10–12", style: "Equations and deeper reasoning", icon: "👩" },
  Expert: { audience: "College+", style: "Technical detail and full context", icon: "🎓" },
};

const contributionLabels = {
  NOBEL_LINKED: "Nobel Prize Contribution",
  BEYOND_NOBEL: "Beyond the Nobel Prize",
};

const connectionLabels = {
  APPLICATION: { icon: "◆", label: "Real-World Application" },
  EXPERIMENTAL_VALIDATION: { icon: "◎", label: "Experimental Validation" },
  SCIENTIFIC_LEGACY: { icon: "↗", label: "Scientific Legacy" },
};

function parseKeyConcepts(keyConcepts) {
  const separator = keyConcepts.includes("\n") ? /\n/ : /,/;
  return keyConcepts
    .split(separator)
    .map((concept) => concept.trim())
    .filter(Boolean);
}

function parseExplanationParagraphs(explanationText) {
  return explanationText
    .split(/\n\s*\n/)
    .map((paragraph) => paragraph.trim())
    .filter(Boolean);
}

function EducationSectionTabs({ activeSection, onChange }) {
  function handleKeyDown(event) {
    const currentIndex = educationSections.findIndex((section) => section.id === activeSection);
    let nextIndex = null;

    if (event.key === "ArrowRight") nextIndex = (currentIndex + 1) % educationSections.length;
    if (event.key === "ArrowLeft") nextIndex = (currentIndex - 1 + educationSections.length) % educationSections.length;
    if (event.key === "Home") nextIndex = 0;
    if (event.key === "End") nextIndex = educationSections.length - 1;
    if (nextIndex === null) return;

    event.preventDefault();
    onChange(educationSections[nextIndex].id);
    event.currentTarget.parentElement.children[nextIndex].focus();
  }

  return (
    <div className="education-section-tabs" role="tablist" aria-label="Educational sections">
      {educationSections.map((section) => (
        <button
          className={`education-section-tab${activeSection === section.id ? " education-section-tab--active" : ""}`}
          id={`education-tab-${section.id}`}
          type="button"
          role="tab"
          aria-controls={`education-panel-${section.id}`}
          aria-selected={activeSection === section.id}
          tabIndex={activeSection === section.id ? 0 : -1}
          onClick={() => onChange(section.id)}
          onKeyDown={handleKeyDown}
          key={section.id}
        >
          {section.label}
        </button>
      ))}
    </div>
  );
}

function ContributionSelector({ contributions, laureateName, selectedId, onSelect }) {
  return (
    <section className="contribution-section" id="contributions" aria-labelledby="contributions-title">
      <div className="detail-section-heading">
        <p className="eyebrow">Explore the work</p>
        <h2 id="contributions-title">Explore {laureateName}’s Ideas</h2>
        <p className="contribution-subtitle">Discover the science, understand the impact, and see how these ideas shape our world today.</p>
      </div>
      <div className="contribution-selector" role="list">
        {contributions.map((contribution) => {
          const selected = contribution.contribution_id === selectedId;
          const visual = getContributionVisual(contribution.title);
          return (
            <button
              className={`contribution-option${selected ? " contribution-option--active" : ""}`}
              type="button"
              role="listitem"
              aria-pressed={selected}
              onClick={() => onSelect(contribution.contribution_id)}
              key={contribution.contribution_id}
            >
              <EducationalVisual visual={visual} compact />
              <span className="contribution-option-copy">
                <strong>{contribution.title}</strong>
                <span className={`contribution-type contribution-type--${contribution.contribution_type.toLowerCase()}`}>
                  {contributionLabels[contribution.contribution_type]}
                </span>
                {contribution.summary && <span className="contribution-summary">{contribution.summary}</span>}
              </span>
              <span className="contribution-arrow" aria-hidden="true">›</span>
            </button>
          );
        })}
      </div>
    </section>
  );
}

function LearningSection({ contribution, explanations, level, onLevelChange }) {
  if (!explanations.length) {
    return (
      <EducationalEmptyState title="Explanations coming soon">
        Learning-level explanations have not been added for this contribution.
      </EducationalEmptyState>
    );
  }

  const explanation = explanations.find((item) => item.level === level) || explanations[0];
  const levelDetail = levelDetails[explanation.level];
  const visual = getContributionVisual(contribution.title);

  return (
    <section className="learning-panel" id="learn" aria-labelledby="learn-title">
      <div className="detail-section-heading">
        <p className="eyebrow">Learn at your level</p>
        <h2 id="learn-title">Understand the idea</h2>
      </div>
      <div className="learning-tabs" role="tablist" aria-label="Explanation level">
        {levels.map((item) => {
          const available = explanations.some((explanationItem) => explanationItem.level === item);
          return (
            <button
              className={item === explanation.level ? "learning-tab learning-tab--active" : "learning-tab"}
              type="button"
              role="tab"
              aria-selected={item === explanation.level}
              disabled={!available}
              onClick={() => onLevelChange(item)}
              key={item}
            >
              <span className="level-icon" aria-hidden="true">{levelDetails[item].icon}</span>
              <strong>{item}</strong>
              <span>{levelDetails[item].audience}</span>
              <small>{levelDetails[item].style}</small>
            </button>
          );
        })}
      </div>
      <div className={`selected-level-heading selected-level-heading--${explanation.level.toLowerCase()}`}>
        <span className="level-icon" aria-hidden="true">{levelDetail.icon}</span>
        <div><strong>{explanation.level} — {levelDetail.audience}</strong><span>{levelDetail.style}</span></div>
      </div>
      <div className={`learning-layout learning-layout--${explanation.level.toLowerCase()}`} role="tabpanel">
        <div className="learning-copy">
          <h3>How it works</h3>
          {parseExplanationParagraphs(explanation.explanation_text).map((paragraph) => (
            <p key={paragraph}>{paragraph}</p>
          ))}
        </div>
        {explanation.key_concepts && (
          <div className="key-concepts">
            <strong>Key concepts</strong>
            <ul>
              {parseKeyConcepts(explanation.key_concepts).map((concept) => (
                <li key={concept}>{concept}</li>
              ))}
            </ul>
          </div>
        )}
        <div className={`visual-learning visual-learning--${explanation.level.toLowerCase()}`}>
          <EducationalVisual visual={visual} level={explanation.level} />
        </div>
      </div>
    </section>
  );
}

function ConnectionsSection({ connections }) {
  return (
    <section className="connections-section" id="connections" aria-labelledby="connections-title">
      <div className="detail-section-heading">
        <p className="eyebrow">Connect the idea</p>
        <h2 id="connections-title">Applications, evidence, and legacy</h2>
      </div>
      {connections.length ? (
        <div className="connection-grid">
          {connections.map((connection) => (
            <article className="connection-card" key={connection.connection_id}>
              <EducationalVisual visual={getConnectionVisual(connection.title)} compact />
              <span className={`connection-type connection-type--${connection.connection_type.toLowerCase()}`}>
                <span aria-hidden="true">{connectionLabels[connection.connection_type].icon}</span>
                {connectionLabels[connection.connection_type].label}
              </span>
              <h3>{connection.title}</h3>
              {connection.description && <p>{connection.description}</p>}
              <div className="connection-actions">
                {connection.source_url && (
                  <a href={connection.source_url} target="_blank" rel="noreferrer">
                    Source <span aria-hidden="true">↗</span>
                  </a>
                )}
                {connection.related_prize && (
                  <Link to={`/prizes/${connection.related_prize.prize_id}`}>
                    Explore the {connection.related_prize.year} {connection.related_prize.category} Prize →
                  </Link>
                )}
              </div>
            </article>
          ))}
        </div>
      ) : (
        <EducationalEmptyState title="Connections coming soon">
          Applications and scientific connections have not been added yet.
        </EducationalEmptyState>
      )}
    </section>
  );
}

function QuizSection({ contributionId, level, questionCount, status }) {
  return (
    <section className="quiz-preview" id="quiz" aria-labelledby="quiz-title">
      <div className="detail-section-heading">
        <p className="eyebrow">Test your knowledge</p>
        <h2 id="quiz-title">Test Your Knowledge</h2>
        <p>Challenge yourself with an interactive quiz about this contribution.</p>
      </div>
      {status === "loading" && <p className="education-status">Loading quiz…</p>}
      {status === "error" && <p className="education-status education-status--error">Quiz could not be loaded.</p>}
      {status === "success" && !questionCount && (
        <p className="education-status">No quiz questions are available for this contribution yet.</p>
      )}
      {status === "success" && questionCount > 0 && (
        <>
          <p className="education-status">
            {questionCount} quiz question{questionCount === 1 ? "" : "s"} available.
          </p>
          <Link
            className="button button-primary"
            to={`/quiz?contribution=${contributionId}&level=${level}`}
          >
            Take Interactive Quiz <span aria-hidden="true">→</span>
          </Link>
        </>
      )}
    </section>
  );
}

const sectionIds = educationSections.map((section) => section.id);

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

function EducationalContent({ contributions, laureateName }) {
  const [searchParams, setSearchParams] = useSearchParams();

  const requestedSection = searchParams.get("section");
  const requestedLevel = searchParams.get("level");

  const [selectedId, setSelectedId] = useState(contributions[0]?.contribution_id ?? null);
  const [activeSection, setActiveSection] = useState(
    sectionIds.includes(requestedSection) ? requestedSection : "learn",
  );
  const [level, setLevel] = useState(levels.includes(requestedLevel) ? requestedLevel : "Simple");
  const [detail, setDetail] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [status, setStatus] = useState("loading");
  const [quizStatus, setQuizStatus] = useState("loading");

  useEffect(() => {
    const requestedId = Number(searchParams.get("contribution"));
    const requestedIsValid = contributions.some(
      (contribution) => contribution.contribution_id === requestedId,
    );
    setSelectedId(requestedIsValid ? requestedId : contributions[0]?.contribution_id ?? null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [contributions]);

  function handleSelectContribution(contributionId) {
    setSelectedId(contributionId);
    updateSearchParams(setSearchParams, { contribution: contributionId });
  }

  function handleSectionChange(sectionId) {
    setActiveSection(sectionId);
    updateSearchParams(setSearchParams, { section: sectionId });
  }

  function handleLevelChange(nextLevel) {
    setLevel(nextLevel);
    updateSearchParams(setSearchParams, { level: nextLevel });
  }

  useEffect(() => {
    if (!selectedId) return undefined;
    const controller = new AbortController();
    setStatus("loading");
    setQuizStatus("loading");

    getContributionById(selectedId, { signal: controller.signal })
      .then((data) => {
        setDetail(data);
        setStatus("success");
      })
      .catch((error) => {
        if (error.name !== "AbortError") setStatus("error");
      });

    getContributionQuiz(selectedId, { signal: controller.signal })
      .then((data) => {
        setQuestions(data);
        setQuizStatus("success");
      })
      .catch((error) => {
        if (error.name !== "AbortError") setQuizStatus("error");
      });

    return () => controller.abort();
  }, [selectedId]);

  return (
    <div className="educational-content">
      <EducationSectionTabs activeSection={activeSection} onChange={handleSectionChange} />
      <div
        className="education-workspace education-section-panel"
        id={`education-panel-${activeSection}`}
        role="tabpanel"
        aria-labelledby={`education-tab-${activeSection}`}
      >
        {activeSection === "explore" && (
          <ContributionSelector contributions={contributions} laureateName={laureateName} selectedId={selectedId} onSelect={handleSelectContribution} />
        )}
        {activeSection !== "explore" && status === "loading" && (
          <p className="education-status" role="status">Loading educational content…</p>
        )}
        {activeSection !== "explore" && status === "error" && (
          <EducationalEmptyState title="Educational content unavailable">
            This contribution could not be loaded. The Laureate information above is still available.
          </EducationalEmptyState>
        )}
        {status === "success" && detail && activeSection === "learn" && (
          <div className="education-main">
            <LearningSection contribution={detail} explanations={detail.explanations} level={level} onLevelChange={handleLevelChange} />
          </div>
        )}
        {status === "success" && detail && activeSection === "impact" && (
          detail.significance ? (
            <section className="why-it-matters">
              <span aria-hidden="true">★</span>
              <div><strong>Why it matters</strong><p>{detail.significance}</p></div>
            </section>
          ) : (
            <EducationalEmptyState title="Impact coming soon">
              Significance information has not been added for this contribution yet.
            </EducationalEmptyState>
          )
        )}
        {status === "success" && detail && activeSection === "applications" && (
          <ConnectionsSection connections={detail.connections} />
        )}
        {status === "success" && detail && activeSection === "quiz" && (
          <QuizSection
            contributionId={selectedId}
            level={level}
            questionCount={questions.length}
            status={quizStatus}
          />
        )}
      </div>
    </div>
  );
}

export default EducationalContent;
