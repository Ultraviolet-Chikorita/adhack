import "@/index.css";

import {
  AlertTriangle,
  BadgeCheck,
  CircleDollarSign,
  FileCheck2,
  Gauge,
  PauseCircle,
  Play,
  RefreshCw,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";
import {
  guardrailSnapshotSchema,
  policyRiskScore,
  type GuardrailSnapshot,
} from "@/api-contract.js";
import { useCallTool, useToolInfo } from "@/helpers.js";

const emptySnapshot: GuardrailSnapshot = {
  apiOnline: false,
  apiBase: "unknown",
  generatedAt: "",
  source: "loading",
};

function getStructuredContent(data: unknown): GuardrailSnapshot | undefined {
  if (!data || typeof data !== "object") {
    return undefined;
  }

  const maybeData = data as { structuredContent?: unknown };
  const structured = maybeData.structuredContent ?? data;

  if (
    structured &&
    typeof structured === "object" &&
    "snapshot" in structured
  ) {
    const parsed = guardrailSnapshotSchema.safeParse(
      (structured as { snapshot?: unknown }).snapshot,
    );
    return parsed.success ? parsed.data : undefined;
  }

  const parsed = guardrailSnapshotSchema.safeParse(structured);
  return parsed.success ? parsed.data : undefined;
}

export default function GuardrailConsole() {
  const toolInfo = useToolInfo<"show_guardrail_console">();
  const initialSnapshot =
    toolInfo.isSuccess && toolInfo.output
      ? guardrailSnapshotSchema.safeParse(toolInfo.output).data ?? emptySnapshot
      : emptySnapshot;
  const [snapshot, setSnapshot] = useState<GuardrailSnapshot>(initialSnapshot);
  const [lastAction, setLastAction] = useState("Console loaded");

  const refresh = useCallTool("show_guardrail_console");
  const runDemo = useCallTool("run_guardrail_demo");
  const bid = useCallTool("evaluate_conversational_bid");
  const creative = useCallTool("judge_inline_creative");
  const waste = useCallTool("evaluate_placement_waste");

  useEffect(() => {
    if (toolInfo.isSuccess && toolInfo.output) {
      const parsed = guardrailSnapshotSchema.safeParse(toolInfo.output);
      if (parsed.success) {
        setSnapshot(parsed.data);
      }
    }
  }, [toolInfo.isSuccess, toolInfo.output]);

  const pending = [
    refresh,
    runDemo,
    bid,
    creative,
    waste,
  ].some((tool) => tool.isPending);

  const flags = snapshot.report?.flags ?? {};
  const summary = snapshot.detail?.summary ?? {};
  const contracts = snapshot.report?.contracts ?? [];
  const approvals = snapshot.detail?.approvals ?? [];
  const events = snapshot.report?.latest_policy_events ?? [];
  const riskScore = policyRiskScore(snapshot.report);

  const statusText = useMemo(() => {
    if (!snapshot.apiOnline) {
      return `API offline at ${snapshot.apiBase}`;
    }

    return `Risk score ${riskScore}; ${flags.money_escalations ?? 0} money escalations; ${
      flags.creative_blocks ?? 0
    } creative blocks; ${flags.auto_paused_placements ?? 0} auto-paused placements.`;
  }, [flags, riskScore, snapshot]);

  async function updateFromCall(
    label: string,
    call: () => Promise<unknown>,
  ) {
    setLastAction(`${label}...`);
    const result = await call();
    const next = getStructuredContent(result);
    if (next) {
      setSnapshot(next);
    }
    setLastAction(label);
  }

  return (
    <main
      className="gb-shell"
      data-llm={statusText}
      aria-busy={pending}
    >
      <header className="gb-header">
        <div>
          <p className="gb-eyebrow">GuardrailBidder · Skybridge App</p>
          <h1>Conversational ad control room</h1>
        </div>
        <div className={`gb-live ${snapshot.apiOnline ? "gb-ok" : "gb-bad"}`}>
          <span />
          {snapshot.apiOnline ? "Python agent online" : "Python agent offline"}
        </div>
      </header>

      <section className="gb-command">
        <button
          type="button"
          onClick={() =>
            updateFromCall("Refreshed", () => refresh.callToolAsync())
          }
          disabled={pending}
        >
          <RefreshCw size={16} />
          Refresh
        </button>
        <button
          type="button"
          className="gb-primary"
          onClick={() =>
            updateFromCall("Seeded demo completed", () => runDemo.callToolAsync())
          }
          disabled={pending}
        >
          <Play size={16} />
          Run demo
        </button>
        <button
          type="button"
          onClick={() =>
            updateFromCall("Spike bid tested", () =>
              bid.callToolAsync({
                prompt:
                  "Best CRM for a 50-person agency, pricing, demo, and enterprise trial.",
                placement_id: "chatgpt-sponsored-answer-1",
              }),
            )
          }
          disabled={pending}
        >
          <CircleDollarSign size={16} />
          Test spike
        </button>
        <button
          type="button"
          onClick={() =>
            updateFromCall("Creative safety tested", () =>
              creative.callToolAsync({
                headline: "NorthstarCRM Guaranteed Growth",
                body: "Guaranteed 3x revenue in 30 days with zero effort.",
                claim: "Guaranteed 3x revenue in 30 days",
              }),
            )
          }
          disabled={pending}
        >
          <FileCheck2 size={16} />
          Test creative
        </button>
        <button
          type="button"
          onClick={() =>
            updateFromCall("Waste policy tested", () =>
              waste.callToolAsync({
                placement_id: "chatgpt-sponsored-answer-1",
                impressions: 640,
                clicks: 42,
                spend: 2.1,
                revenue: 0.9,
              }),
            )
          }
          disabled={pending}
        >
          <PauseCircle size={16} />
          Test waste
        </button>
      </section>

      {!snapshot.apiOnline ? (
        <section className="gb-alert" role="alert">
          <AlertTriangle />
          <div>
            <strong>Agent API unavailable</strong>
            <p>{snapshot.error ?? "Start the FastAPI service on port 8000."}</p>
          </div>
        </section>
      ) : null}

      <section className="gb-metrics">
        <Metric
          icon={<Gauge />}
          label="Risk score"
          value={`${riskScore}`}
          tone={riskScore === 0 ? "good" : riskScore >= 50 ? "bad" : "warn"}
        />
        <Metric
          icon={<CircleDollarSign />}
          label="Money escalations"
          value={flags.money_escalations ?? 0}
          tone={(flags.money_escalations ?? 0) > 0 ? "warn" : "neutral"}
        />
        <Metric
          icon={<ShieldCheck />}
          label="Creative blocks"
          value={flags.creative_blocks ?? 0}
          tone={(flags.creative_blocks ?? 0) > 0 ? "bad" : "neutral"}
        />
        <Metric
          icon={<PauseCircle />}
          label="Auto-pauses"
          value={flags.auto_paused_placements ?? 0}
          tone={(flags.auto_paused_placements ?? 0) > 0 ? "warn" : "neutral"}
        />
      </section>

      <section className="gb-grid">
        <Panel title="Human boundary contracts" icon={<BadgeCheck />}>
          <div className="gb-contracts">
            {contracts.map((contract) => (
              <article
                key={contract.name}
                className={contract.status === "FLAGGED" ? "gb-flagged" : ""}
              >
                <div>
                  <strong>{contract.name}</strong>
                  <span>{contract.status}</span>
                </div>
                <p>{contract.agent_can_act}</p>
                <small>{contract.human_boundary}</small>
              </article>
            ))}
          </div>
        </Panel>

        <Panel title="Sponsor surfaces" icon={<Sparkles />}>
          <div className="gb-sponsors">
            <Sponsor label="Overmind" value={snapshot.detail?.supervision?.enabled ? "tracing" : "local"} />
            <Sponsor label="Alpic MCP" value={snapshot.detail?.mcp?.endpoint ?? "pending"} />
            <Sponsor label="Skybridge" value="interactive MCP app" />
            <Sponsor label="Tavily" value="claim grounding visible in trace" />
          </div>
          <p className="gb-note">
            Last action: {lastAction}. Total spend ${Number(summary.total_spend ?? 0).toFixed(2)};
            approvals {summary.pending_approvals ?? approvals.filter((a) => a.status === "pending").length};
            traces {summary.trace_count ?? 0}.
          </p>
        </Panel>
      </section>

      <section className="gb-grid">
        <Panel title="Approval queue" icon={<AlertTriangle />}>
          <div className="gb-list">
            {approvals.length ? (
              approvals.slice(0, 5).map((approval) => (
                <article key={approval.id}>
                  <span>{approval.escalation_type}</span>
                  <strong>{approval.reason}</strong>
                  <small>{approval.status}</small>
                </article>
              ))
            ) : (
              <p className="gb-empty">No approval items yet.</p>
            )}
          </div>
        </Panel>

        <Panel title="Latest policy hits" icon={<ShieldCheck />}>
          <div className="gb-timeline">
            {events.length ? (
              events.slice(0, 7).map((event) => (
                <article key={event.id}>
                  <strong>{String(event.payload.policy ?? event.event_type)}</strong>
                  <span>{String(event.payload.outcome ?? event.message)}</span>
                </article>
              ))
            ) : (
              <p className="gb-empty">Run the seeded demo to populate the trace.</p>
            )}
          </div>
        </Panel>
      </section>
    </main>
  );
}

function Metric({
  icon,
  label,
  value,
  tone,
}: {
  icon: ReactNode;
  label: string;
  value: string | number;
  tone: "good" | "warn" | "bad" | "neutral";
}) {
  return (
    <article className={`gb-metric gb-${tone}`}>
      <div>{icon}</div>
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

function Panel({
  title,
  icon,
  children,
}: {
  title: string;
  icon: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="gb-panel">
      <div className="gb-panel-title">
        {icon}
        <h2>{title}</h2>
      </div>
      {children}
    </section>
  );
}

function Sponsor({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
