import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import TabBar from "./components/TabBar";
import { Toaster, OfflineIndicator } from "./components/ui";
import { AuthProvider } from "./auth/AuthContext";
import { RequireKey } from "./auth/RequireKey";
import { SettingsProvider } from "./lib/settings";
import { routes } from "./config/routes";
import NotFound from "./components/NotFound";

function AppContent() {
  const location = useLocation();

  // Hide TabBar on enter-key and setup pages, show otherwise
  const showTabBar = location.pathname !== "/enter-key" && location.pathname !== "/setup";

  const renderRoute = (route: typeof routes[0]) => {
    const Component = route.component;
    if (!Component) {
      console.error(`Missing component for route: ${route.path}`);
      return (
        <Route
          key={route.path}
          path={route.path}
          element={<NotFound />}
        />
      );
    }
    const element = <Component />;

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
        <SettingsProvider>
          <AppContent />
          <OfflineIndicator />
          <Toaster />
        </SettingsProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
