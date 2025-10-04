import { BrowserRouter, Routes, Route } from "react-router-dom";
import Home from "./pages/Home";
import Plate from "./pages/Plate";
import Progress from "./pages/Progress";
import Profile from "./pages/Profile";
import TabBar from "./components/TabBar";
import { Toaster, OfflineIndicator } from "./components/ui";

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-dvh bg-navy text-text pb-14">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/plate" element={<Plate />} />
          <Route path="/progress" element={<Progress />} />
          <Route path="/profile" element={<Profile />} />
        </Routes>
        <TabBar />
      </div>
      <OfflineIndicator />
      <Toaster />
    </BrowserRouter>
  );
}
