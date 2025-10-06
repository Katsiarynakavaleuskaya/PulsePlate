import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import Home from "./pages/Home";
import Plate from "./pages/Plate";
import Progress from "./pages/Progress";
import Profile from "./pages/Profile";
import EnterKey from "./pages/Onboarding/EnterKey";
import TabBar from "./components/TabBar";
import { Toaster, OfflineIndicator } from "./components/ui";
import { AuthProvider } from "./auth/AuthContext";
import { RequireKey } from "./auth/RequireKey";
import { routes } from "./config/routes";

function AppContent() {
  const location = useLocation();

  // Hide TabBar on enter-key page, show otherwise
  const showTabBar = location.pathname !== "/enter-key";

  const renderRoute = (route: typeof routes[0]) => {
    const element = route.path === "/" ? <Home /> :
                   route.path === "/enter-key" ? <EnterKey /> :
                   route.path === "/profile" ? <Profile /> :
                   route.path === "/plate" ? <Plate /> :
                   route.path === "/progress" ? <Progress /> :
                   <div>Page not found</div>;

    return (
      <Route
        key={route.path}
        path={route.path}
        element={route.requiresAuth ? <RequireKey>{element}</RequireKey> : element}
      />
    );
  };

  return (
    <div className="min-h-dvh bg-navy text-text pb-14">
      <Routes>
        {routes.map(renderRoute)}
      </Routes>
      {showTabBar && <TabBar />}
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppContent />
        <OfflineIndicator />
        <Toaster />
      </AuthProvider>
    </BrowserRouter>
  );
}
