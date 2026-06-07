import { useEffect, useState } from "react";

import { fetchPortfolioScan } from "../api";
import type { PortfolioScan } from "../types";

interface PortfolioBoardProps {
  onInvestigate: (term: string) => void;
  busy: boolean;
}

function formatValue(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
}

function isScan(value: unknown): value is PortfolioScan {
  return (
    typeof value === "object" &&
    value !== null &&
    Array.isArray((value as PortfolioScan).concepts) &&
    typeof (value as PortfolioScan).score === "object"
  );
}

export function PortfolioBoard({ onInvestigate, busy }: PortfolioBoardProps) {
  const [scan, setScan] = useState<PortfolioScan | null>(null);

  useEffect(() => {
    let active = true;
    fetchPortfolioScan()
      .then((data) => {
        if (active && isScan(data)) {
          setScan(data);
        }
      })
      .catch(() => {
        /* The board is optional context; stay silent if the scan is unavailable. */
      });
    return () => {
      active = false;
    };
  }, []);

  if (!scan) {
    return null;
  }

  const { score } = scan;
  return (
    <section className="portfolio-board surface" aria-labelledby="portfolio-title">
      <div className="portfolio-head">
        <div>
          <span className="section-kicker">Autonomous semantic scan</span>
          <h2 id="portfolio-title">Where the business silently disagrees</h2>
          <p>
            Concord IQ swept {score.concepts_scanned} governed concepts and ranked every
            conflict by business impact — including the ones it checked and cleared.
          </p>
        </div>
        <div className={`score-dial grade-${score.grade}`} aria-label="Concord Score">
          <strong>{score.overall}</strong>
          <span>Concord Score</span>
          <em>grade {score.grade}</em>
        </div>
      </div>

      <div className="score-summary">
        <span>
          <strong>{score.conflicts}</strong> conflicts
        </span>
        <span>
          <strong>{score.consistent}</strong> consistent
        </span>
        <span>
          <strong>{score.refusals}</strong> refusal{score.refusals === 1 ? "" : "s"}
        </span>
      </div>

      <ol className="conflict-board">
        {scan.concepts.map((item) => (
          <li key={item.concept_id} className={`conflict-row verdict-${item.verdict}`}>
            <span className="conflict-rank">{item.rank ? `#${item.rank}` : "OK"}</span>
            <div className="conflict-main">
              <strong>{item.term}</strong>
              <span className="conflict-counts">{item.counts.join(" / ")}</span>
            </div>
            <div className="conflict-impact">
              <strong>{formatValue(item.arr_delta)}</strong>
              <span>{item.customer_count_delta} entity delta</span>
            </div>
            <span className={`action-pill action-${item.recommended_action}`}>
              {item.recommended_action}
            </span>
            <button
              type="button"
              className="ghost-button"
              disabled={busy}
              onClick={() => onInvestigate(item.term)}
            >
              Investigate
            </button>
          </li>
        ))}
      </ol>

      <div className="team-leaderboard">
        <span className="section-kicker">Team semantic health</span>
        <div className="team-grid">
          {score.by_business_unit.map((unit) => (
            <div key={unit.business_unit} className="team-card">
              <strong>{unit.score}</strong>
              <span>{unit.business_unit}</span>
              <em>{unit.open_conflicts} open</em>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
