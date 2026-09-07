import { Link } from "react-router-dom";

function PrizePageState({ title, children, retry, backTo = "/prizes", backLabel = "Back to Prizes" }) {
  return (
    <section className="prize-page-state" role={retry ? "alert" : undefined}>
      <span aria-hidden="true">✦</span>
      <h1>{title}</h1>
      <p>{children}</p>
      <div className="prize-state-actions">
        {retry && (
          <button className="button button-primary" type="button" onClick={retry}>Retry</button>
        )}
        <Link className="button button-secondary" to={backTo}>{backLabel}</Link>
      </div>
    </section>
  );
}

export default PrizePageState;
