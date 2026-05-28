import "@/index.css";

import {
  AlertTriangle,
  BadgeCheck,
  CircleDollarSign,
  PauseCircle,
  ShieldCheck,
} from "lucide-react";
import { decisionOutputSchema, policyRiskScore, type DecisionOutput } from "@/api-contract.js";

type DecisionToolInfo = {
  isSuccess: boolean;
  output?: unknown;
};

type DecisionPanelViewProps = {
  toolInfo: DecisionToolInfo;
  defaultKind: "bid" | "creative" | "waste";
};

export function DecisionPanelView({ toolInfo, defaultKind }: DecisionPanelViewProps) {
  const parsed = toolInfo.isSuccess
    ? decisionOutputSchema.safeParse(toolInfo.output)
    : undefined;
  const output: DecisionOutput | undefined = parsed?.success ? parsed.data : undefined;
  const kind = output?.kind ?? defaultKind;
  const result = output?.result ?? {};

  const title =
    kind === "creative"
      ? "Creative judgement"
      : kind === "waste"
        ? "Waste decision"
        : "Bid decision";

  const icon =
    kind === "creative" ? (
      <ShieldCheck />
    ) : kind === "waste" ? (
      <PauseCircle />
    ) : (
      <CircleDollarSign />
    );

  const riskScore = policyRiskScore(output?.snapshot?.report);

  return (
    <main className="gb-shell gb-compact" data-llm={decisionSummary(kind, result)}>
      <header className="gb-header">
        <div>
          <p className="gb-eyebrow">GuardrailBidder · Skybridge App</p>
          <h1>{title}</h1>
        </div>
        <div className="gb-live gb-ok">
          <span />
          Tool-backed review
        </div>
      </header>

      <section className="gb-decision">
        <div className="gb-decision-icon">{icon}</div>
        <div>
          <p className="gb-eyebrow">{kind}</p>
          <h2>{decisionHeadline(kind, result)}</h2>
          <p>{decisionReason(kind, result)}</p>
        </div>
      </section>

      <section className="gb-json-grid">
        <JsonBlock title="Tool result" value={result} />
        <JsonBlock
          title="Current policy posture"
          value={{
            risk_score: riskScore,
            flags: output?.snapshot?.report?.flags,
          }}
        />
      </section>

      <section className="gb-handoff">
        <AlertTriangle />
        <p>
          The model receives this structured decision and the view exposes the same state
          through <code>data-llm</code>, so follow-up questions stay grounded in the
          actual guardrail outcome.
        </p>
      </section>
    </main>
  );
}

function decisionHeadline(kind: string, result: Record<string, unknown>) {
  if (kind === "creative") {
    const judgement = result.judgement as Record<string, unknown> | undefined;
    return `Verdict: ${String(judgement?.verdict ?? "unknown")}`;
  }

  if (kind === "waste") {
    return Boolean(result.auto_paused) ? "Placement auto-paused" : "Placement still active";
  }

  const bid = result.bid as Record<string, unknown> | undefined;
  if (!bid) {
    return "Awaiting bid result";
  }
  return Boolean(bid.requires_human)
    ? "Human approval required"
    : Boolean(bid.approved)
      ? "Agent may commit spend"
      : "Agent did not bid";
}

function decisionReason(kind: string, result: Record<string, unknown>) {
  if (kind === "creative") {
    const judgement = result.judgement as Record<string, unknown> | undefined;
    const source = judgement?.source_url ? ` Source: ${String(judgement.source_url)}` : "";
    return `${String(judgement?.reason ?? "No reason returned.")}${source}`;
  }

  if (kind === "waste") {
    return String(result.message ?? "No waste message returned.");
  }

  const bid = result.bid as Record<string, unknown> | undefined;
  const intent = result.intent as Record<string, unknown> | undefined;
  return `Intent ${String(intent?.score ?? "unknown")} from ${String(
    intent?.source ?? "unknown",
  )}. ${String(bid?.reason ?? "No bid reason returned.")}`;
}

function decisionSummary(kind: string, result: Record<string, unknown>) {
  return `${kind} decision: ${decisionHeadline(kind, result)}. ${decisionReason(
    kind,
    result,
  )}`;
}

function JsonBlock({ title, value }: { title: string; value: unknown }) {
  return (
    <article className="gb-json">
      <div>
        <BadgeCheck size={16} />
        <strong>{title}</strong>
      </div>
      <pre>{JSON.stringify(value, null, 2)}</pre>
    </article>
  );
}
