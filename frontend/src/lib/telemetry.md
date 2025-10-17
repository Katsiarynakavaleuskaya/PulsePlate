# VIP Telemetry Foundation

## Overview

The VIP Telemetry system provides comprehensive event tracking for VIP features and user interactions. It's designed to be type-safe, feature-flag aware, and easily extensible.

## Architecture

### Core Components

1. **`telemetry.ts`** - Core telemetry functions and type definitions
2. **`useTelemetry.ts`** - React hooks for component integration
3. **Event Types** - Type-safe event definitions with payload validation

### Event Types

The system tracks the following VIP-specific events:

- `vip_module_viewed` - When VIP module is accessed
- `vip_feature_clicked` - When a VIP feature is interacted with
- `vip_paywall_viewed` - When paywall is displayed
- `vip_paywall_dismissed` - When paywall is closed
- `vip_upgrade_clicked` - When upgrade CTA is clicked
- `vip_gate_interacted` - When VIP gate is interacted with
- `vip_badge_viewed` - When VIP badge is displayed

## Usage

### Basic Telemetry

```typescript
import { vipTelemetry } from '../lib/telemetry';

// Track a VIP feature click
vipTelemetry.featureClicked('advanced_analytics', 'dashboard', false);

// Track paywall view
vipTelemetry.paywallViewed('dashboard', 'feature_gate', true);
```

### React Hook Integration

```typescript
import { useTelemetry } from '../lib/useTelemetry';

function VipFeature() {
  const { track, isEnabled, isVip } = useTelemetry();

  const handleFeatureClick = () => {
    track.featureClicked('advanced_analytics', 'dashboard');
  };

  return (
    <button onClick={handleFeatureClick}>
      Advanced Analytics
    </button>
  );
}
```

### Auto-tracking VIP Module Views

```typescript
import { useVipModuleTracking } from '../lib/useTelemetry';

function VipDashboard() {
  // Automatically tracks module view on mount
  useVipModuleTracking('dashboard');

  return <div>VIP Dashboard</div>;
}
```

## Event Payloads

### Base Event Structure

All events include:

- `timestamp` - Event occurrence time
- `sessionId` - User session identifier (optional)
- `featureFlags` - Feature flag state (optional)

### VIP-Specific Payloads

#### VipModuleViewedPayload

```typescript
{
  source: string;        // Source page/component
  vipEnabled: boolean;   // VIP module state
}
```

#### VipFeatureClickedPayload

```typescript
{
  featureName: string;   // Name of VIP feature
  source: string;        // Component/page context
  isVip: boolean;        // User VIP status
}
```

#### VipPaywallViewedPayload

```typescript
{
  source: string;        // Trigger source
  context: string;       // Paywall context
  isRetry?: boolean;     // Retry indicator
}
```

## Integration with Components

### VipGate Integration

The `VipGate` component automatically tracks:

- Gate interactions (clicks, hovers)
- Upgrade button clicks
- Paywall views and dismissals

### VipBadge Integration

The `VipBadge` component automatically tracks:

- Badge views on component mount
- Component and variant information

## Feature Flag Integration

Telemetry respects the `VITE_ANALYTICS_ENABLED` feature flag:

- When `false` - No events are tracked
- When `true` (default) - All events are tracked

## Testing

### Mocking Telemetry

```typescript
import { vi } from 'vitest';

const mockUseTelemetry = vi.fn();
vi.mock('../lib/useTelemetry', () => ({
  useTelemetry: () => mockUseTelemetry(),
}));

// Setup mock in tests
mockUseTelemetry.mockReturnValue({
  track: {
    featureClicked: vi.fn(),
    // ... other track functions
  },
  isEnabled: true,
  isVip: false,
});
```

### Testing Event Tracking

```typescript
it('should track feature click', () => {
  const mockTrack = { featureClicked: vi.fn() };
  mockUseTelemetry.mockReturnValue({ track: mockTrack, isEnabled: true, isVip: false });

  render(<VipFeature />);
  fireEvent.click(screen.getByRole('button'));

  expect(mockTrack.featureClicked).toHaveBeenCalledWith('advanced_analytics', 'dashboard');
});
```

## Future Extensions

### Adding New Events

1. Add event type to `VipEventType` union
2. Define payload interface extending `BaseEventPayload`
3. Add to `VipEventPayload` union
4. Add convenience function to `vipTelemetry` object
5. Add hook method to `useTelemetry`

### Example: Adding `vip_tutorial_started`

```typescript
// 1. Add to VipEventType
export type VipEventType =
  | 'vip_tutorial_started'
  | // ... existing types

// 2. Define payload
export interface VipTutorialStartedPayload extends BaseEventPayload {
  tutorialId: string;
  source: string;
}

// 3. Add to union
export type VipEventPayload =
  | VipTutorialStartedPayload
  | // ... existing payloads

// 4. Add convenience function
export const vipTelemetry = {
  tutorialStarted: (tutorialId: string, source: string) => {
    trackVipEvent('vip_tutorial_started', { tutorialId, source });
  },
  // ... existing functions
};

// 5. Add hook method
export function useTelemetry() {
  const track = {
    tutorialStarted: useCallback((tutorialId: string, source: string) => {
      if (!isEnabled) return;
      vipTelemetry.tutorialStarted(tutorialId, source);
    }, [isEnabled]),
    // ... existing methods
  };
}
```

## Performance Considerations

- Events are only tracked when analytics is enabled
- Timestamps are added automatically if not provided
- Hook functions are memoized to prevent unnecessary re-renders
- Telemetry calls are non-blocking and don't affect UI performance

## Privacy and Compliance

- All events are logged to console in development
- No personal data is collected in event payloads
- Feature flag integration allows easy disabling
- Events can be filtered by VIP status for privacy
