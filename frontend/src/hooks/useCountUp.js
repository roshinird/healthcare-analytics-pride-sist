/**
 * Animate a number from 0 to `value` on first arrival and between values on
 * change. Used by the KPI cards so a figure reads as freshly computed rather
 * than pre-printed.
 *
 * Respects `prefers-reduced-motion`: reduced-motion users get the final value
 * immediately, with no intermediate frames.
 */

import { useEffect, useRef, useState } from 'react';

const DURATION_MS = 900;
const easeOut = (t) => 1 - Math.pow(1 - t, 3);

export function prefersReducedMotion() {
  return (
    typeof window !== 'undefined' &&
    typeof window.matchMedia === 'function' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches
  );
}

/**
 * @param {number|null|undefined} value
 * @param {{ duration?: number, enabled?: boolean }} [options]
 * @returns {number}
 */
export function useCountUp(value, { duration = DURATION_MS, enabled = true } = {}) {
  const target = Number.isFinite(value) ? Number(value) : 0;
  const [displayed, setDisplayed] = useState(target);
  const fromRef = useRef(target);

  useEffect(() => {
    if (!enabled || prefersReducedMotion() || typeof requestAnimationFrame !== 'function') {
      fromRef.current = target;
      setDisplayed(target);
      return undefined;
    }

    const from = fromRef.current;
    if (from === target) return undefined;

    let frame;
    const start = performance.now();

    const step = (now) => {
      const progress = Math.min((now - start) / duration, 1);
      setDisplayed(from + (target - from) * easeOut(progress));
      if (progress < 1) {
        frame = requestAnimationFrame(step);
      } else {
        fromRef.current = target;
      }
    };

    frame = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frame);
  }, [target, duration, enabled]);

  return displayed;
}
