import { BrowserRouter, Routes, Route } from "react-router-dom";
import Studio from "./pages/Studio";
import HomePage from "./pages/HomePage";
import Lobby from "./pages/Lobby";
import "./App.css";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/lobby/:id" element={<Lobby />} />
        <Route path="/studio/:id" element={<Studio />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
