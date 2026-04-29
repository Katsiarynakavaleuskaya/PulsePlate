import { ComponentType } from 'react';
import Home from '../pages/Home';
import Plate from '../pages/Plate';
import Progress from '../pages/Progress';
import Profile from '../pages/Profile';
import EnterKey from '../pages/Onboarding/EnterKey';
import WelcomeGateV1 from '../pages/Onboarding/WelcomeGateV1';
import NutritionSetup from '../pages/NutritionSetup';
import BMICalculatePage from '../pages/BMI/BMICalculatePage';
import ProPaywallPage from '../pages/Pro/ProPaywallPage';
import DesignSystemPage from '../pages/DesignSystemPage';
import PulsePlateMarketingPage from '../pages/Marketing/PulsePlateMarketingPage';

export interface RouteConfig {
  path: string;
  label: string;
  requiresAuth: boolean;
  component: ComponentType;
  hideTabBar?: boolean;
  requiresVip?: boolean;
}

// Union type for all route paths to ensure exhaustiveness
export type RoutePath =
  | '/'
  | '/app'
  | '/marketing'
  | '/enter-key'
  | '/setup'
  | '/profile'
  | '/plate'
  | '/progress'
  | '/bmi'
  | '/pro'
  | '/design-system'
  | '/welcome-gate-v1';

export const routes: RouteConfig[] = [
  {
    path: '/',
    label: 'Launch',
    requiresAuth: false,
    component: PulsePlateMarketingPage,
    hideTabBar: true,
  },
  { path: '/app', label: 'Home', requiresAuth: false, component: Home },
  {
    path: '/marketing',
    label: 'Marketing',
    requiresAuth: false,
    component: PulsePlateMarketingPage,
    hideTabBar: true,
  },
  { path: '/enter-key', label: 'EnterKey', requiresAuth: false, component: EnterKey, hideTabBar: true },
  { path: '/setup', label: 'Setup', requiresAuth: false, component: NutritionSetup, hideTabBar: true },
  { path: '/profile', label: 'Profile', requiresAuth: false, component: Profile },
  { path: '/plate', label: 'Plate', requiresAuth: true, component: Plate },
  { path: '/progress', label: 'Progress', requiresAuth: true, component: Progress },
  { path: '/bmi', label: 'BMI', requiresAuth: false, component: BMICalculatePage, hideTabBar: true },
  { path: '/pro', label: 'Pro', requiresAuth: false, component: ProPaywallPage, hideTabBar: true },
  { path: '/design-system', label: 'DesignSystem', requiresAuth: false, component: DesignSystemPage, hideTabBar: true },
  {
    path: '/welcome-gate-v1',
    label: 'WelcomeGateV1',
    requiresAuth: false,
    component: WelcomeGateV1,
    hideTabBar: true,
  },
];

// Compile-time check: ensure all RoutePath values are present in routes
// If you add a new route to RoutePath, you must add it to routes array
// If you add a route to routes array, you must add it to RoutePath union
type RoutePathsInConfig = typeof routes[number]['path'];
// This will cause a TypeScript error if routes don't match RoutePath union exactly
export type _AssertRoutesExhaustive = [RoutePath] extends [RoutePathsInConfig]
  ? [RoutePathsInConfig] extends [RoutePath]
    ? true
    : never
  : never;

// Routes that should appear in the tab bar (excluding pages with hideTabBar: true)
export const tabRoutes = routes.filter(route => !route.hideTabBar);
