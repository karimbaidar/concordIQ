import type { UngovernedTermRefusal } from "../types";

interface UngovernedRefusalCardProps {
  refusal: UngovernedTermRefusal;
  busy: boolean;
  onInvestigate: (term: string) => void;
}

/**
 * A friendly, first-class refusal for a term with no governed definition.
 *
 * Distinct from the authority RefusalCard: this is the anti-hallucination boundary
 * — Concord IQ will not invent a definition it cannot ground, and instead points to
 * the governed terms it can actually reconcile.
 */
export function UngovernedRefusalCard({
  refusal,
  busy,
  onInvestigate,
}: UngovernedRefusalCardProps) {
  return (
    <section
      className="surface ungoverned-refusal"
      aria-labelledby="ungoverned-title"
      role="status"
    >
      <span className="section-kicker">No governed definition</span>
      <h2 id="ungoverned-title">Concord IQ will not guess “{refusal.term}”</h2>
      <p>{refusal.reason}</p>
      {refusal.known_terms.length > 0 && (
        <div className="ungoverned-suggestions">
          <span>Terms Concord IQ can reconcile today:</span>
          <div className="ungoverned-chips">
            {refusal.known_terms.map((term) => (
              <button
                key={term}
                type="button"
                className="ghost-button"
                disabled={busy}
                onClick={() => onInvestigate(term)}
              >
                {term}
              </button>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
