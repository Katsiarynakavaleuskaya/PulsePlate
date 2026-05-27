import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  guidedPlanningObservabilitySensitiveFields,
  setGuidedPlanningEventSink,
  trackGuidedPlanningEvent,
  type GuidedPlanningEventPayload,
} from '../mvpObservability';

const allowedPayloadKeys = ['surface', 'componentId', 'routePath', 'optionId', 'tierLabel'];

describe('mvpObservability', () => {
  const originalSendBeacon = navigator.sendBeacon;

  afterEach(() => {
    setGuidedPlanningEventSink(null);
    vi.unstubAllGlobals();
    Object.defineProperty(navigator, 'sendBeacon', {
      configurable: true,
      value: originalSendBeacon,
    });
    vi.restoreAllMocks();
  });

  it('emits typed frontend-only guided planning events to the local sink', () => {
    const events: Array<{ name: string; payload: GuidedPlanningEventPayload }> = [];
    setGuidedPlanningEventSink((event) => events.push(event));

    trackGuidedPlanningEvent('planning_intent_selected', {
      surface: 'app',
      componentId: 'planning-intent-selector',
      routePath: '/app',
      optionId: 'shopping',
    });

    expect(events).toEqual([
      {
        name: 'planning_intent_selected',
        payload: {
          surface: 'app',
          componentId: 'planning-intent-selector',
          routePath: '/app',
          optionId: 'shopping',
        },
      },
    ]);
  });

  it('keeps MVP event payloads allowlisted and free of sensitive field names', () => {
    const events: Array<{ payload: GuidedPlanningEventPayload }> = [];
    setGuidedPlanningEventSink((event) => events.push(event));

    trackGuidedPlanningEvent('primary_planning_cta_clicked', {
      surface: 'app',
      componentId: 'primary-planning-cta',
      routePath: '/setup',
    });

    const payloadKeys = Object.keys(events[0].payload);
    expect(payloadKeys.every((key) => allowedPayloadKeys.includes(key))).toBe(true);
    expect(payloadKeys).not.toEqual(expect.arrayContaining([...guidedPlanningObservabilitySensitiveFields]));
  });

  it('does not use browser storage, cookies, network, or analytics transports', () => {
    const fetchSpy = vi.fn();
    const sendBeaconSpy = vi.fn();
    const storageSetItemSpy = vi.spyOn(Storage.prototype, 'setItem');
    vi.stubGlobal('fetch', fetchSpy);
    Object.defineProperty(navigator, 'sendBeacon', {
      configurable: true,
      value: sendBeaconSpy,
    });

    trackGuidedPlanningEvent('guided_planning_viewed', {
      surface: 'app',
      componentId: 'guided-planning-preview',
      routePath: '/app',
    });

    expect(fetchSpy).not.toHaveBeenCalled();
    expect(storageSetItemSpy).not.toHaveBeenCalled();
    expect(sendBeaconSpy).not.toHaveBeenCalled();
    expect(document.cookie).toBe('');
  });
});
