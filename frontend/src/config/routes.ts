import { ComponentType } from 'react';
import Home from '../pages/Home';
import Plate from '../pages/Plate';
import Progress from '../pages/Progress';
import Profile from '../pages/Profile';
import EnterKey from '../pages/Onboarding/EnterKey';

export interface RouteConfig {
  path: string;
  label: string;
  requiresAuth: boolean;
  component: ComponentType;
}

// Union type for all route paths to ensure exhaustiveness
export type RoutePath = '/' | '/enter-key' | '/profile' | '/plate' | '/progress';

export const routes: RouteConfig[] = [
  { path: '/', label: 'Home', requiresAuth: false, component: Home },
  { path: '/enter-key', label: 'EnterKey', requiresAuth: false, component: EnterKey },
  { path: '/profile', label: 'Profile', requiresAuth: false, component: Profile },
  { path: '/plate', label: 'Plate', requiresAuth: true, component: Plate },
  { path: '/progress', label: 'Progress', requiresAuth: true, component: Progress },
];

// Compile-time check: ensure all RoutePath values are present in routes
// If you add a new route to RoutePath, you must add it to routes array
// If you add a route to routes array, you must add it to RoutePath union
type RoutePathsInConfig = typeof routes[number]['path'];
// This will cause a TypeScript error if routes don't match RoutePath union exactly
type _AssertRoutesExhaustive = RoutePath extends RoutePathsInConfig
  ? RoutePathsInConfig extends RoutePath
    ? true
    : never
  : never;

// Routes that should appear in the tab bar (excluding pages like enter-key)
export const tabRoutes = routes.filter(route => route.path !== '/enter-key');
