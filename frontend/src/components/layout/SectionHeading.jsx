/**
 * Section heading.
 *
 * The dashboard is grouped into four analytical themes rather than one flat wall
 * of charts. Each heading names the theme and the questions it covers, so the
 * page reads as an argument instead of a gallery.
 */

export default function SectionHeading({ eyebrow, title, description, id }) {
  return (
    <div className="mb-4 max-w-3xl" id={id}>
      <span className="eyebrow">{eyebrow}</span>
      <h2 className="mt-1.5 text-lg font-semibold text-ink">{title}</h2>
      {description ? (
        <p className="mt-1 text-sm leading-relaxed text-ink-muted">{description}</p>
      ) : null}
    </div>
  );
}
