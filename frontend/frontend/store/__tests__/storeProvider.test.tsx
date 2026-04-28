// Tests for StoreProvider: validation rejection (Property 12), cross-tab sync (Property 9),
// and sync edge cases (Requirements 4.1, 4.4, 4.5)

import React from 'react';
import * as fc from 'fast-check';
import { render, act } from '@testing-library/react';
import {
  StoreProvider,
  StoreContext,
  DEFAULT_STATE,
} from '@/frontend/store/index';
import type { AppState, AppAction } from '@/frontend/store/index';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** A test consumer that reads state from context and exposes dispatch */
function TestConsumer({
  onRender,
}: {
  onRender: (ctx: { state: AppState; dispatch: React.Dispatch<AppAction> }) => void;
}) {
  const ctx = React.useContext(StoreContext);
  onRender(ctx);
  return null;
}

/** Build a mock BroadcastChannel class, returning the instance and mocks */
function makeMockBroadcastChannel() {
  const postMessageMock = jest.fn();
  const closeMock = jest.fn();
  let messageHandler: ((event: MessageEvent) => void) | null = null;

  class MockBroadcastChannel {
    static lastInstance: MockBroadcastChannel | null = null;
    static constructorArgs: string[] = [];

    postMessage = postMessageMock;
    close = closeMock;

    get onmessage() { return messageHandler; }
    set onmessage(handler: ((event: MessageEvent) => void) | null) {
      messageHandler = handler;
    }

    constructor(name: string) {
      MockBroadcastChannel.constructorArgs.push(name);
      MockBroadcastChannel.lastInstance = this;
    }
  }

  const triggerMessage = (data: unknown) => {
    if (messageHandler) {
      messageHandler(new MessageEvent('message', { data }));
    }
  };

  return { MockBroadcastChannel, postMessageMock, closeMock, triggerMessage };
}

// ---------------------------------------------------------------------------
// Task 6.2 — Property 12: Invalid action is rejected with error
// Feature: advanced-state-management, Property 12: Invalid action is rejected with error
// Validates: Requirements 7.1, 7.2, 7.3
// ---------------------------------------------------------------------------

describe('Property 12: Invalid action is rejected with error', () => {
  it('state is unchanged and onValidationError is called when dispatch produces invalid state', () => {
    // The dispatch wrapper in StoreProvider calls validateState on the next state.
    // We test this by dispatching @@HYDRATE with a payload that produces invalid state
    // (e.g. setting ui.theme to an invalid value). Since @@HYDRATE merges the payload
    // into present state, we can craft payloads that break the schema.
    fc.assert(
      fc.property(
        fc.oneof(
          fc.string().filter(s => s !== 'light' && s !== 'dark'),
          fc.integer(),
          fc.boolean(),
          fc.constant(null),
        ),
        (badTheme) => {
          const validationErrorSpy = jest.fn();
          let capturedState: AppState = DEFAULT_STATE;
          let capturedDispatch!: React.Dispatch<AppAction>;

          const { unmount } = render(
            React.createElement(StoreProvider, {
              onValidationError: validationErrorSpy,
              children: React.createElement(TestConsumer, {
                onRender: (ctx) => {
                  capturedState = ctx.state;
                  capturedDispatch = ctx.dispatch;
                },
              }),
            }),
          );

          // Reset spy after mount (hydration may trigger validation)
          validationErrorSpy.mockClear();

          // Dispatch @@HYDRATE with an invalid ui.theme — this produces invalid state
          act(() => {
            capturedDispatch({
              type: '@@HYDRATE',
              payload: { ui: { theme: badTheme as 'light' | 'dark', sidebarOpen: false } },
            });
          });

          // State must remain DEFAULT_STATE (unchanged — transition rejected)
          expect(capturedState).toEqual(DEFAULT_STATE);
          // onValidationError must have been called with a non-empty errors array
          expect(validationErrorSpy).toHaveBeenCalledWith(
            expect.arrayContaining([
              expect.objectContaining({ field: expect.any(String) }),
            ]),
          );

          unmount();
        },
      ),
      { numRuns: 20 },
    );
  });
});

// ---------------------------------------------------------------------------
// Task 6.4 — Property 9: No re-broadcast on receive
// Feature: advanced-state-management, Property 9: No re-broadcast on receive
// Validates: Requirements 4.3
// ---------------------------------------------------------------------------

describe('Property 9: No re-broadcast on receive', () => {
  let originalBC: unknown;

  beforeEach(() => {
    originalBC = (global as Record<string, unknown>).BroadcastChannel;
  });

  afterEach(() => {
    (global as Record<string, unknown>).BroadcastChannel = originalBC;
  });

  it('applying a received broadcast message does not call channel.postMessage again', () => {
    fc.assert(
      fc.property(
        fc.record({
          version: fc.constant(1),
          ui: fc.record({
            theme: fc.oneof(fc.constant('light' as const), fc.constant('dark' as const)),
            sidebarOpen: fc.boolean(),
          }),
          classification: fc.record({
            result: fc.constant(null),
            isLoading: fc.boolean(),
            error: fc.oneof(fc.constant(null), fc.string()),
          }),
          user: fc.record({
            preferences: fc.record({
              language: fc.string({ minLength: 1, maxLength: 10 }),
              notifications: fc.boolean(),
            }),
          }),
        }),
        (incomingState) => {
          const { MockBroadcastChannel, postMessageMock, triggerMessage } = makeMockBroadcastChannel();
          (global as Record<string, unknown>).BroadcastChannel = MockBroadcastChannel;

          const { unmount } = render(
            React.createElement(StoreProvider, { children: null }),
          );

          // Clear any postMessage calls from initial mount/persist effects
          postMessageMock.mockClear();

          // Simulate receiving a broadcast message from another tab
          act(() => {
            triggerMessage(incomingState);
          });

          // postMessage must NOT have been called after receiving a broadcast
          expect(postMessageMock).not.toHaveBeenCalled();

          unmount();
        },
      ),
      { numRuns: 20 },
    );
  });
});

// ---------------------------------------------------------------------------
// Task 6.5 — Unit tests for sync edge cases
// ---------------------------------------------------------------------------

describe('Sync edge cases', () => {
  let originalBC: unknown;

  beforeEach(() => {
    originalBC = (global as Record<string, unknown>).BroadcastChannel;
  });

  afterEach(() => {
    (global as Record<string, unknown>).BroadcastChannel = originalBC;
  });

  // Requirement 4.1: BroadcastChannel name is 'app_state_sync' on init
  it('opens BroadcastChannel named app_state_sync on mount (Requirement 4.1)', () => {
    const { MockBroadcastChannel } = makeMockBroadcastChannel();
    (global as Record<string, unknown>).BroadcastChannel = MockBroadcastChannel;

    const { unmount } = render(React.createElement(StoreProvider, { children: null }));

    expect(MockBroadcastChannel.constructorArgs).toContain('app_state_sync');

    unmount();
  });

  // Requirement 4.5: Channel is closed on unmount
  it('closes BroadcastChannel on unmount (Requirement 4.5)', () => {
    const { MockBroadcastChannel, closeMock } = makeMockBroadcastChannel();
    (global as Record<string, unknown>).BroadcastChannel = MockBroadcastChannel;

    const { unmount } = render(React.createElement(StoreProvider, { children: null }));

    unmount();

    expect(closeMock).toHaveBeenCalled();
  });

  // Requirement 4.4: Falls back to storage event when BroadcastChannel unavailable
  it('falls back to window storage event when BroadcastChannel is unavailable (Requirement 4.4)', () => {
    // Remove BroadcastChannel from global
    delete (global as Record<string, unknown>).BroadcastChannel;

    const addEventListenerSpy = jest.spyOn(window, 'addEventListener');
    const removeEventListenerSpy = jest.spyOn(window, 'removeEventListener');

    const { unmount } = render(React.createElement(StoreProvider, { children: null }));

    // Should have registered a 'storage' event listener
    expect(addEventListenerSpy).toHaveBeenCalledWith('storage', expect.any(Function));

    unmount();

    // Should have removed the 'storage' event listener on unmount
    expect(removeEventListenerSpy).toHaveBeenCalledWith('storage', expect.any(Function));

    addEventListenerSpy.mockRestore();
    removeEventListenerSpy.mockRestore();
  });
});
