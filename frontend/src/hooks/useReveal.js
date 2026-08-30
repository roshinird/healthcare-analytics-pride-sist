/**
 * Reveal an element the first time it scrolls into view.
 *
 * Returns a ref and a boolean. Falls back to "already revealed" wherever
 * IntersectionObserver is unavailable (jsdom in tests, older browsers) so
 * content is never hidden by a missing API.
 */

import { useEffect, useRef, useState } from 'react';

export function useReveal({ rootMargin = '0px 0px -60px 0px' } = {}) {
  const ref = useRef(null);
  const [revealed, setRevealed] = useState(
    () => typeof IntersectionObserver === 'undefined',
  );

  useEffect(() => {
    if (revealed || typeof IntersectionObserver === 'undefined') return undefined;
    const element = ref.current;
    if (!element) return undefined;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setRevealed(true);
          observer.disconnect();
        }
      },
      { rootMargin, threshold: 0.05 },
    );

    observer.observe(element);
    return () => observer.disconnect();
  }, [revealed, rootMargin]);

  return [ref, revealed];
}
