export interface RouteConfig {
  path: string;
  label: string;
  requiresAuth: boolean;
}

export const routes: RouteConfig[] = [
  { path: '/', label: 'Home', requiresAuth: false },
  { path: '/enter-key', label: 'EnterKey', requiresAuth: false },
  { path: '/profile', label: 'Profile', requiresAuth: false },
  { path: '/plate', label: 'Plate', requiresAuth: true },
  { path: '/progress', label: 'Progress', requiresAuth: true },
];

// Routes that should appear in the tab bar (excluding pages like enter-key)
export const tabRoutes = routes.filter(route => route.path !== '/enter-key');
