import { BrowserRouter, Routes, Route } from "react-router-dom";
import Home from "./pages/Home";
import Plate from "./pages/Plate";
import Progress from "./pages/Progress";
import Profile from "./pages/Profile";
import EnterKey from "./pages/Onboarding/EnterKey";
import TabBar from "./components/TabBar";
import { Toaster, OfflineIndicator } from "./components/ui";
import { AuthProvider } from "./auth/AuthContext";
import { RequireKey } from "./auth/RequireKey";

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <div className="min-h-dvh bg-navy text-text pb-14">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/enter-key" element={<EnterKey />} />
            <Route
              path="/plate"
              element={
                <RequireKey>
                  <Plate />
                </RequireKey>
              }
            />
            <Route path="/progress" element={<Progress />} />
            <Route
              path="/profile"
              element={
                <RequireKey>
                  <Profile />
                </RequireKey>
              }
            />
          </Routes>
          <TabBar />
        </div>
        <OfflineIndicator />
        <Toaster />
      </BrowserRouter>
    </AuthProvider>
  );
}
