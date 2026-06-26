import { BrowserRouter, Routes, Route } from "react-router-dom";
import Studio from "./pages/Studio";
import HomePage from "./pages/HomePage";
import "./App.css";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/discussion/:id" element={<Studio />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
