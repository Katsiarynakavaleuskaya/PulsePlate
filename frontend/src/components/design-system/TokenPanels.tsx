import { paletteTokens, radiusSamples, spacingSamples, typographySamples } from './data';
import { PanelShell } from './shared';

export function PalettePanel() {
  return (
    <PanelShell title="Brand Palette" subtitle="Five canonical colors from token SoT">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        {paletteTokens.map((token) => (
          <div key={token.name} className="rounded-2xl border border-white/8 bg-white/[0.03] p-3">
            <div className="h-20 rounded-xl border border-white/10" style={{ backgroundColor: token.value }} />
            <p className="mt-3 text-sm font-semibold text-white">{token.name}</p>
            <p className="mt-1 font-mono text-[11px] uppercase tracking-[0.12em] text-white/35">{token.variable}</p>
            <p className="mt-2 text-xs text-white/55">{token.role}</p>
            <p className="mt-2 text-xs text-white/72">{token.value}</p>
          </div>
        ))}
      </div>
    </PanelShell>
  );
}

export function TypographyPanel() {
  return (
    <PanelShell title="Typography" subtitle="Restrained hierarchy with calm premium tone">
      <div className="space-y-4">
        {typographySamples.map((sample) => (
          <div key={sample.label} className="rounded-2xl border border-white/8 bg-white/[0.02] p-4">
            <p className="mb-2 text-[11px] uppercase tracking-[0.22em] text-white/35">{sample.label}</p>
            <p
              style={{
                fontSize: sample.fontSize,
                fontWeight: sample.fontWeight,
                lineHeight: sample.lineHeight,
                letterSpacing: sample.letterSpacing,
              }}
              className={[
                sample.label === 'Caption' ? 'uppercase text-white/42' : 'text-white',
                sample.label === 'Body' ? 'text-white/72' : '',
              ].join(' ').trim()}
            >
              {sample.sample}
            </p>
          </div>
        ))}
      </div>
    </PanelShell>
  );
}

export function SpacingRadiusPanel() {
  return (
    <PanelShell title="Spacing + Radius" subtitle="Measured rhythm instead of decorative noise">
      <div className="space-y-4">
        {spacingSamples.map((space) => (
          <div key={space.label} className="grid grid-cols-[60px_minmax(0,1fr)] items-center gap-3">
            <p className="font-mono text-xs text-white/40">{space.label}</p>
            <div className="h-3 rounded-full bg-white/[0.06]">
              <div className="h-3 rounded-full bg-[var(--pp-blue)]" style={{ width: space.value }} />
            </div>
          </div>
        ))}
      </div>
      <div className="mt-5 grid grid-cols-3 gap-3">
        {radiusSamples.map((radius) => (
          <div key={radius.label} className="rounded-2xl border border-white/8 bg-white/[0.03] p-3 text-center">
            <div
              className="mx-auto h-12 w-full max-w-[88px] border border-dashed border-white/15 bg-white/[0.04]"
              style={{ borderRadius: radius.value }}
            />
            <p className="mt-3 text-xs text-white/58">{radius.label}</p>
          </div>
        ))}
      </div>
    </PanelShell>
  );
}
