import { useState } from 'react';
import { FitChefMascot, PulsePlateLogo } from '../brand';
import { BrandIdentityPanel, LogoVariantsPanel } from './BrandPanels';
import { ComponentShowcasePanel, GovernancePanel, PlatformInventoryPanel } from './ExperiencePanels';
import { PalettePanel, SpacingRadiusPanel, TypographyPanel } from './TokenPanels';
import { DesignSystemCanvas, OverviewHeader } from './shared';

export function DesignSystemOverview() {
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);

  return (
    <DesignSystemCanvas>
      <header className="relative overflow-hidden rounded-[28px] border border-white/10 bg-white/[0.04] px-6 py-8 shadow-[0_28px_80px_rgba(0,0,0,0.34)] sm:px-8">
        <div className="absolute inset-x-0 top-0 h-px bg-white/10" />
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_240px] lg:items-center">
          <div>
            <div className="inline-flex items-center gap-3 rounded-full border border-white/10 bg-white/[0.04] px-4 py-2 text-[11px] uppercase tracking-[0.26em] text-white/50">
              <span className="h-2 w-2 rounded-full bg-[var(--pp-green)]" />
              Storybook-first Design System
            </div>
            <div className="mt-5">
              <PulsePlateLogo variant="lockup" />
            </div>
            <h1 className="mt-5 text-4xl font-semibold tracking-[-0.05em] text-white sm:text-5xl">
              PulsePlate Design System
            </h1>
            <p className="mt-4 max-w-3xl text-base leading-7 text-white/68">
              A production-oriented design system surface built from reusable React panels, canonical brand assets,
              and Storybook documentation aligned to the current token source of truth.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <span className="rounded-full bg-white/[0.06] px-3 py-2 text-sm text-white/70">Repo-native review</span>
              <span className="rounded-full bg-[rgba(51,159,255,0.14)] px-3 py-2 text-sm text-[var(--pp-blue)]">
                Penpot-ready handoff
              </span>
              <span className="rounded-full bg-[rgba(212,175,55,0.12)] px-3 py-2 text-sm text-[var(--pp-gold)]">
                Real brand assets imported
              </span>
              <span className="rounded-full bg-[rgba(32,201,151,0.12)] px-3 py-2 text-sm text-[var(--pp-green)]">
                tokens.css aligned
              </span>
            </div>
          </div>
          <div className="rounded-[24px] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.08),rgba(255,255,255,0.02))] p-4">
            <FitChefMascot className="mx-auto" size="lg" variant="wink" />
          </div>
        </div>
      </header>

      <section className="mt-10">
        <OverviewHeader
          description="Fixed naming, bilingual tagline, core mood tokens, and the visual direction the product should keep across web surfaces."
          eyebrow="1. Brand Identity"
          title="Brand core, mascot, and logo system"
        />
        <div className="grid gap-6 lg:grid-cols-2">
          <BrandIdentityPanel />
          <LogoVariantsPanel />
        </div>
      </section>

      <section className="mt-10">
        <OverviewHeader
          description="The Figma spec uses a disciplined navy system with bright utility accents. These panels bind the visual language to the token layer already present in the repository."
          eyebrow="2. Core Tokens"
          title="Palette, typography, spacing, and shape"
        />
        <div className="grid gap-6 xl:grid-cols-[1.25fr_1fr]">
          <PalettePanel />
          <div className="grid gap-6">
            <TypographyPanel />
            <SpacingRadiusPanel />
          </div>
        </div>
      </section>

      <section className="mt-10">
        <OverviewHeader
          description="Shared controls are shown with the current primitives and token surfaces instead of a one-off route implementation."
          eyebrow="3. Shared Components"
          title="Component showcase for Storybook review"
        />
        <ComponentShowcasePanel
          notificationsEnabled={notificationsEnabled}
          onNotificationsChange={setNotificationsEnabled}
        />
      </section>

      <section className="mt-10">
        <OverviewHeader
          description="This inventory and governance layer keeps implementation scope aligned across web, iOS, and shared components while preventing visual drift."
          eyebrow="4. Inventory + Governance"
          title="Coverage map and anti-drift rules"
        />
        <div className="grid gap-6">
          <PlatformInventoryPanel />
          <GovernancePanel />
        </div>
      </section>
    </DesignSystemCanvas>
  );
}

export default DesignSystemOverview;
