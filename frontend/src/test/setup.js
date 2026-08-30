import '@testing-library/jest-dom/vitest';
import { afterEach, vi } from 'vitest';
import { cleanup } from '@testing-library/react';

afterEach(cleanup);

// Recharts' ResponsiveContainer measures its parent, which jsdom reports as 0×0.
// Stubbing the observer with a fixed box lets charts actually render in tests.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = globalThis.ResizeObserver ?? ResizeObserverStub;

Object.defineProperty(globalThis.window, 'matchMedia', {
  writable: true,
  value: (query) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }),
});

for (const prop of ['offsetWidth', 'offsetHeight']) {
  Object.defineProperty(globalThis.window.HTMLElement.prototype, prop, {
    configurable: true,
    value: prop === 'offsetWidth' ? 800 : 400,
  });
}
