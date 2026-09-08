import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import App from "./App";
import "./styles/variables.css";
import "./styles/global.css";
import "./styles/components.css";
import "./styles/home.css";
import "./styles/laureates.css";
import "./styles/laureate-detail.css";
import "./styles/prizes.css";
import "./styles/analytics.css";
import "./styles/learn.css";
import "./styles/quiz.css";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
);
