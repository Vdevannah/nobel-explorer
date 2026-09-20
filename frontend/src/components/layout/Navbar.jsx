import { useEffect, useState } from "react";
import { Link, NavLink } from "react-router-dom";

import nobelExplorerLogo from "../../assets/branding/nobel-explorer-logo-navbar.png";
import nobelExplorerLightLogo from "../../assets/branding/nobel-explorer-logo-navbar-light.png";

function Navbar() {
  const [theme, setTheme] = useState(() => document.documentElement.dataset.theme || "light");

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try {
      localStorage.setItem("nobel-explorer-theme", theme);
    } catch {
      // The control still works for this visit when browser storage is blocked.
    }
  }, [theme]);

  return (
    <header className="site-header">
      <nav className="navbar container" aria-label="Primary navigation">
        <Link className="brand" to="/" aria-label="Nobel Explorer home">
          <img className="brand-logo" src={theme === "light" ? nobelExplorerLightLogo : nobelExplorerLogo} alt="Nobel Explorer" />
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
          <button
            className="theme-toggle"
            type="button"
            aria-label="Dark theme"
            aria-pressed={theme === "dark"}
            onClick={() => setTheme((current) => current === "light" ? "dark" : "light")}
          >
            <span aria-hidden="true">{theme === "light" ? "☀" : "☾"}</span>
            {theme === "light" ? "Light" : "Dark"}
          </button>
        </div>
      </nav>
    </header>
  );
}

export default Navbar;
