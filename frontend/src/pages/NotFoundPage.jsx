import { Link } from "react-router-dom";

function NotFoundPage() {
  return (
    <section className="not-found container">
      <p className="eyebrow">Page not found</p>
      <h1>This discovery is still waiting to be made.</h1>
      <p>The page you requested does not exist.</p>
      <Link className="button button-primary" to="/">
        Return Home
      </Link>
    </section>
  );
}

export default NotFoundPage;
