import { Link, NavLink } from "react-router-dom";

function Navbar() {
  return (
    <header className="site-header">
      <nav className="navbar container" aria-label="Primary navigation">
        <Link className="brand" to="/" aria-label="Nobel Explorer home">
          <span className="brand-mark" aria-hidden="true">
            <span>N</span>
          </span>
          <span>Nobel Explorer</span>
        </Link>

        <div className="nav-links">
          <NavLink
            className={({ isActive }) =>
              isActive ? "nav-link nav-link-active" : "nav-link"
            }
            to="/"
            end
          >
            Home
          </NavLink>
          <NavLink
            className={({ isActive }) =>
              isActive ? "nav-link nav-link-active" : "nav-link"
            }
            to="/prizes"
          >
            Explore Prizes
          </NavLink>
          <NavLink
            className={({ isActive }) =>
              isActive ? "nav-link nav-link-active" : "nav-link"
            }
            to="/laureates"
          >
            Browse Laureates
          </NavLink>
          <NavLink
            className={({ isActive }) =>
              isActive ? "nav-link nav-link-active" : "nav-link"
            }
            to="/analytics"
          >
            Analytics
          </NavLink>
          <NavLink
            className={({ isActive }) =>
              isActive ? "nav-link nav-link-active" : "nav-link"
            }
            to="/learn"
          >
            Learn
          </NavLink>
          <NavLink
            className={({ isActive }) =>
              isActive ? "nav-link nav-link-active" : "nav-link"
            }
            to="/quiz"
          >
            Quiz
          </NavLink>
        </div>
      </nav>
    </header>
  );
}

export default Navbar;
