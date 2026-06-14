import type { LearningScaleProof as LearningScaleProofType } from "../types";

interface LearningScaleProofProps {
  proof: LearningScaleProofType;
}

const INTEGER_FORMAT = new Intl.NumberFormat("en-US");

export function LearningScaleProof({ proof }: LearningScaleProofProps) {
  return (
    <section className="surface scale-proof" aria-labelledby="scale-proof-title">
      <div className="section-heading">
        <div>
          <span className="section-kicker">Fabric scale artifact</span>
          <h2 id="scale-proof-title">The same concept, seeded at enterprise scale</h2>
        </div>
        <span className="quiet-label">Separate proof surface</span>
      </div>
      <div className="scale-proof-grid">
        <div>
          <strong>{INTEGER_FORMAT.format(proof.learner_count)}</strong>
          <span>synthetic learners</span>
        </div>
        <div>
          <strong>{INTEGER_FORMAT.format(proof.certification_ready_count)}</strong>
          <span>canonical-ready records</span>
        </div>
        <div>
          <strong>{INTEGER_FORMAT.format(proof.false_ready_blocked_count)}</strong>
          <span>false-ready records</span>
        </div>
      </div>
      <p>
        {proof.execution_separation} These values prove the committed Fabric-bound dataset’s
        scale; they are not the source of the workbench’s 80/56/56 result.
      </p>
    </section>
  );
}
