/**
 * Loading skeletons.
 *
 * Spec: docs/09-ui-design-system.md §9 — a pulsing block that occupies the
 * element's *final* dimensions, so nothing shifts when the data lands.
 *
 * The chart skeleton sketches a plausible silhouette rather than showing a flat
 * grey rectangle, so the reader already knows what shape is arriving.
 */

export function SkeletonBlock({ className = '', style }) {
  return <div className={`skeleton ${className}`} style={style} aria-hidden="true" />;
}

export function KpiSkeleton() {
  return (
    <div className="space-y-3" aria-hidden="true">
      <SkeletonBlock className="h-3 w-24" />
      <SkeletonBlock className="h-8 w-32" />
      <SkeletonBlock className="h-3 w-20" />
    </div>
  );
}

const BAR_HEIGHTS = [52, 74, 41, 88, 63, 79, 47, 68];

export default function LoadingSkeleton({
  height = 260,
  variant = 'bars',
  label = 'Loading chart',
}) {
  return (
    <div className="w-full" style={{ height }} role="status" aria-label={label}>
      {variant === 'line' || variant === 'block' ? (
        <SkeletonBlock className="h-full w-full rounded-lg" />
      ) : (
        <div className="flex h-full w-full items-end gap-2 px-1 pb-6">
          {BAR_HEIGHTS.map((value, index) => (
            <SkeletonBlock
              key={index}
              className="w-full rounded-t-md"
              style={{ height: `${value}%` }}
            />
          ))}
        </div>
      )}
      <span className="sr-only">{label}</span>
    </div>
  );
}
