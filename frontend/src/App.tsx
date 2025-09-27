import { BrowserRouter, Routes, Route } from "react-router-dom";

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-dvh bg-navy text-text">
        <Routes>
          <Route path="/" element={<div />} />
          <Route path="/plate" element={<div />} />
          <Route path="/progress" element={<div />} />
          <Route path="/profile" element={<div />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}
