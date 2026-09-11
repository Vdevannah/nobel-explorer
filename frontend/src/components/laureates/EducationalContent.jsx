import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { getContributionById, getContributionQuiz } from "../../services/api";
import { getConnectionVisual, getContributionVisual } from "../../data/educationalVisuals";
import { formatNameList } from "../../utils/nameList";
import EducationalEmptyState from "./EducationalEmptyState";
import EducationalVisual from "./EducationalVisual";

const levels = ["Simple", "Explore", "Advanced", "Expert"];

// How many stored paragraphs are visible by default under the educational
// image before the reader opts into "Read full explanation" -- the full text
// stays in the data either way. Deliberately increasing (not identical) per
// level so Simple stays very short while Expert can carry more by default,
// per the approved level-progression requirement.
const DEFAULT_VISIBLE_PARAGRAPHS = { Simple: 1, Explore: 2, Advanced: 2, Expert: 2 };
const educationSections = [
  { id: "explore", label: "Explore" },
  { id: "learn", label: "Learn" },
  { id: "impact", label: "Impact" },
  { id: "applications", label: "Applications" },
  { id: "quiz", label: "Quiz" },
];

// One coherent line-icon family (shared viewBox/stroke settings) for the
// four learning levels -- no icon library is installed, so these are
// hand-drawn inline SVGs rather than a new dependency.
const LEVEL_ICON_PROPS = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round",
  strokeLinejoin: "round",
  "aria-hidden": "true",
};

function LightbulbIcon() {
  return (
    <svg {...LEVEL_ICON_PROPS}>
      <path d="M9 18h6" />
      <path d="M10 21.5h4" />
      <path d="M12 2.5a6.5 6.5 0 0 0-3.8 11.8c.7.5 1.3 1.5 1.3 2.7h5c0-1.2.6-2.2 1.3-2.7A6.5 6.5 0 0 0 12 2.5Z" />
    </svg>
  );
}

function SearchIcon() {
  return (
    <svg {...LEVEL_ICON_PROPS}>
      <circle cx="11" cy="11" r="7" />
      <line x1="21" y1="21" x2="16.2" y2="16.2" />
    </svg>
  );
}

function FlaskIcon() {
  return (
    <svg {...LEVEL_ICON_PROPS}>
      <path d="M9.5 2h5" />
      <path d="M10.5 2v6.8l-5.3 9.2a1.9 1.9 0 0 0 1.65 2.85h10.3a1.9 1.9 0 0 0 1.65-2.85l-5.3-9.2V2" />
      <path d="M8.3 15h7.4" />
    </svg>
  );
}

function BookOpenIcon() {
  return (
    <svg {...LEVEL_ICON_PROPS}>
      <path d="M12 6.2c-1.6-1.1-3.7-1.7-6.3-1.7v13.2c2.6 0 4.7.6 6.3 1.7c1.6-1.1 3.7-1.7 6.3-1.7V4.5c-2.6 0-4.7.6-6.3 1.7Z" />
      <path d="M12 6.2v13.2" />
    </svg>
  );
}

const levelDetails = {
  Simple: { audience: "Grades 4–6", style: "Everyday language, minimal math", Icon: LightbulbIcon },
  Explore: { audience: "Grades 7–9", style: "Build vocabulary and understanding", Icon: SearchIcon },
  Advanced: { audience: "Grades 10–12", style: "Equations and deeper reasoning", Icon: FlaskIcon },
  Expert: { audience: "College+", style: "Technical detail and full context", Icon: BookOpenIcon },
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

// Frontend-only display override, keyed by connection_id: connection 278
// ("Understanding Innate Immune Recognition of RNA", contribution 609) is
// stored as SCIENTIFIC_LEGACY, but reads more accurately to students as a
// foundational mechanism than a downstream legacy effect. This changes only
// the label shown here -- connection_type in the database, the badge's
// accent styling, the title, description, image, source, and ID are all
// unchanged. Einstein's SCIENTIFIC_LEGACY connections (e.g. Gravitational
// Waves) are untouched and keep showing "Scientific Legacy".
const CONNECTION_LABEL_OVERRIDES = {
  278: "Scientific Foundation",
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
  const [isExplanationExpanded, setIsExplanationExpanded] = useState(false);

  const explanation = explanations.find((item) => item.level === level) || explanations[0];

  // Collapse back to the concise view whenever the level changes, so
  // switching levels never leaves a previous level's "expanded" choice
  // showing under the new image.
  useEffect(() => {
    setIsExplanationExpanded(false);
  }, [explanation?.level]);

  if (!explanations.length) {
    return (
      <EducationalEmptyState title="Explanations coming soon">
        Learning-level explanations have not been added for this contribution.
      </EducationalEmptyState>
    );
  }

  const visual = getContributionVisual(contribution.title);
  const paragraphs = parseExplanationParagraphs(explanation.explanation_text);
  const visibleCount = DEFAULT_VISIBLE_PARAGRAPHS[explanation.level] ?? paragraphs.length;
  const canExpand = paragraphs.length > visibleCount;
  const visibleParagraphs = isExplanationExpanded ? paragraphs : paragraphs.slice(0, visibleCount);

  return (
    <section className="learning-panel" id="learn" aria-labelledby="learn-title">
      <div className="detail-section-heading">
        <p className="eyebrow">Learn at your level</p>
        <h2 id="learn-title">Understand the idea</h2>
        {contribution.credited_laureates?.length > 1 && (
          <p>{formatNameList(contribution.credited_laureates.map((credit) => credit.name))}</p>
        )}
      </div>
      <div className="learning-tabs" role="tablist" aria-label="Explanation level">
        {levels.map((item) => {
          const available = explanations.some((explanationItem) => explanationItem.level === item);
          const TabIcon = levelDetails[item].Icon;
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
              <span className={`level-icon level-icon--${item.toLowerCase()}`}><TabIcon /></span>
              <strong>{item}</strong>
              <span>{levelDetails[item].audience}</span>
              <small>{levelDetails[item].style}</small>
            </button>
          );
        })}
      </div>
      <div className={`learning-layout learning-layout--${explanation.level.toLowerCase()}`} role="tabpanel">
        <div className={`visual-learning visual-learning--${explanation.level.toLowerCase()}`}>
          <EducationalVisual visual={visual} level={explanation.level} />
        </div>
        <div className="learning-copy">
          <h3>How it works</h3>
          {visibleParagraphs.map((paragraph) => (
            <p key={paragraph}>{paragraph}</p>
          ))}
          {canExpand && (
            <button
              type="button"
              className="learning-copy-toggle"
              onClick={() => setIsExplanationExpanded((expanded) => !expanded)}
              aria-expanded={isExplanationExpanded}
            >
              {isExplanationExpanded ? "Show less" : "Read full explanation"}
            </button>
          )}
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
      </div>
    </section>
  );
}

function ConnectionsSection({ connections }) {
  const [selectedConnectionId, setSelectedConnectionId] = useState(
    connections[0]?.connection_id ?? null,
  );

  // Re-select the first application whenever the underlying contribution's
  // connections change, so switching contributions never leaves a stale
  // selection from a previous one.
  useEffect(() => {
    setSelectedConnectionId(connections[0]?.connection_id ?? null);
  }, [connections]);

  const selectedConnection =
    connections.find((connection) => connection.connection_id === selectedConnectionId) ??
    connections[0];

  function handleTabKeyDown(event, currentIndex) {
    let nextIndex = null;
    if (event.key === "ArrowRight") nextIndex = (currentIndex + 1) % connections.length;
    if (event.key === "ArrowLeft") nextIndex = (currentIndex - 1 + connections.length) % connections.length;
    if (event.key === "Home") nextIndex = 0;
    if (event.key === "End") nextIndex = connections.length - 1;
    if (nextIndex === null) return;

    event.preventDefault();
    setSelectedConnectionId(connections[nextIndex].connection_id);
    event.currentTarget.parentElement.children[nextIndex].focus();
  }

  return (
    <section className="connections-section" id="connections" aria-labelledby="connections-title">
      <div className="detail-section-heading">
        <p className="eyebrow">Real-world impact</p>
        <h2 id="connections-title">See how the discovery matters</h2>
      </div>
      {connections.length && selectedConnection ? (
        <div className="connection-experience">
          <div className="connection-tabs" role="tablist" aria-label="Applications and connections">
            {connections.map((connection, index) => (
              <button
                className={`connection-tab${connection.connection_id === selectedConnection.connection_id ? " connection-tab--active" : ""}`}
                type="button"
                role="tab"
                id={`connection-tab-${connection.connection_id}`}
                aria-controls={`connection-panel-${connection.connection_id}`}
                aria-selected={connection.connection_id === selectedConnection.connection_id}
                tabIndex={connection.connection_id === selectedConnection.connection_id ? 0 : -1}
                onClick={() => setSelectedConnectionId(connection.connection_id)}
                onKeyDown={(event) => handleTabKeyDown(event, index)}
                key={connection.connection_id}
              >
                {connection.title}
              </button>
            ))}
          </div>
          <article
            className="connection-featured"
            id={`connection-panel-${selectedConnection.connection_id}`}
            role="tabpanel"
            aria-labelledby={`connection-tab-${selectedConnection.connection_id}`}
          >
            <div className="connection-featured-visual">
              <EducationalVisual visual={getConnectionVisual(selectedConnection.title)} />
            </div>
            <span className={`connection-type connection-type--${selectedConnection.connection_type.toLowerCase()}`}>
              <span aria-hidden="true">{connectionLabels[selectedConnection.connection_type].icon}</span>
              {CONNECTION_LABEL_OVERRIDES[selectedConnection.connection_id] ?? connectionLabels[selectedConnection.connection_type].label}
            </span>
            <h3>{selectedConnection.title}</h3>
            {selectedConnection.description && <p>{selectedConnection.description}</p>}
            <div className="connection-actions">
              {selectedConnection.source_url && (
                <a href={selectedConnection.source_url} target="_blank" rel="noreferrer">
                  Source <span aria-hidden="true">↗</span>
                </a>
              )}
              {selectedConnection.related_prize && (
                <Link to={`/prizes/${selectedConnection.related_prize.prize_id}`}>
                  Explore the {selectedConnection.related_prize.year} {selectedConnection.related_prize.category} Prize →
                </Link>
              )}
            </div>
          </article>
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
