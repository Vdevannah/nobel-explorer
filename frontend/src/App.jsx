import { Route, Routes } from "react-router-dom";

import Navbar from "./components/layout/Navbar";
import AnalyticsPage from "./pages/AnalyticsPage";
import CategoryPage from "./pages/CategoryPage";
import HomePage from "./pages/HomePage";
import LaureateDetailPage from "./pages/LaureateDetailPage";
import LaureatesPage from "./pages/LaureatesPage";
import LearnPage from "./pages/LearnPage";
import NotFoundPage from "./pages/NotFoundPage";
import PrizeDetailPage from "./pages/PrizeDetailPage";
import PrizesPage from "./pages/PrizesPage";
import QuizPage from "./pages/QuizPage";

function App() {
  return (
    <div className="app-shell">
      <Navbar />
      <main>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/prizes" element={<PrizesPage />} />
          <Route path="/prizes/:prizeId" element={<PrizeDetailPage />} />
          <Route path="/categories/:categoryId" element={<CategoryPage />} />
          <Route path="/laureates" element={<LaureatesPage />} />
          <Route path="/laureates/:laureateId" element={<LaureateDetailPage />} />
          <Route path="/learn" element={<LearnPage />} />
          <Route path="/quiz" element={<QuizPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
