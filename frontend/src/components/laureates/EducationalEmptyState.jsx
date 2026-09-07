function EducationalEmptyState({ title, children }) {
  return (
    <section className="educational-empty-state">
      <span aria-hidden="true">✦</span>
      <div>
        <h2>{title}</h2>
        <p>{children}</p>
      </div>
    </section>
  );
}

export default EducationalEmptyState;
