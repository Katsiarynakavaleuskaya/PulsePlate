import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
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
    const Component = route.component;
    if (!Component) {
      console.error(`Missing component for route: ${route.path}`);
      return (
        <Route
          key={route.path}
          path={route.path}
          element={<div>Page not found</div>}
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
        <AppContent />
        <OfflineIndicator />
        <Toaster />
      </AuthProvider>
    </BrowserRouter>
  );
}
