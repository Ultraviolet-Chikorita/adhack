import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import "@/index.css";
import { AlertTriangle, BadgeCheck, CircleDollarSign, FileCheck2, Gauge, PauseCircle, Play, RefreshCw, ShieldCheck, Sparkles, } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useCallTool, useToolInfo } from "@/helpers.js";
const emptySnapshot = {
    apiOnline: false,
    apiBase: "unknown",
    generatedAt: "",
    source: "loading",
};
function getStructuredContent(data) {
    if (!data || typeof data !== "object") {
        return undefined;
    }
    const maybeData = data;
    const structured = maybeData.structuredContent ?? data;
    if (structured &&
        typeof structured === "object" &&
        "snapshot" in structured) {
        return structured.snapshot;
    }
    return structured;
}
export default function GuardrailConsole() {
    const toolInfo = useToolInfo();
    const initialSnapshot = toolInfo.isSuccess && toolInfo.output
        ? toolInfo.output
        : emptySnapshot;
    const [snapshot, setSnapshot] = useState(initialSnapshot);
    const [lastAction, setLastAction] = useState("Console loaded");
    const refresh = useCallTool("show_guardrail_console");
    const runDemo = useCallTool("run_guardrail_demo");
    const bid = useCallTool("evaluate_conversational_bid");
    const creative = useCallTool("judge_inline_creative");
    const waste = useCallTool("evaluate_placement_waste");
    useEffect(() => {
        if (toolInfo.isSuccess && toolInfo.output) {
            setSnapshot(toolInfo.output);
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
    const readiness = snapshot.report?.readiness_score ?? 0;
    const statusText = useMemo(() => {
        if (!snapshot.apiOnline) {
            return `API offline at ${snapshot.apiBase}`;
        }
        return `Readiness ${readiness}; ${flags.money_escalations ?? 0} money escalations; ${flags.creative_blocks ?? 0} creative blocks; ${flags.auto_paused_placements ?? 0} auto-paused placements.`;
    }, [flags, readiness, snapshot]);
    async function updateFromCall(label, call) {
        setLastAction(`${label}...`);
        const result = await call();
        const next = getStructuredContent(result);
        if (next) {
            setSnapshot(next);
        }
        setLastAction(label);
    }
    return (_jsxs("main", { className: "gb-shell", "data-llm": statusText, "aria-busy": pending, children: [_jsxs("header", { className: "gb-header", children: [_jsxs("div", { children: [_jsx("p", { className: "gb-eyebrow", children: "GuardrailBidder \u00B7 Skybridge App" }), _jsx("h1", { children: "Conversational ad control room" })] }), _jsxs("div", { className: `gb-live ${snapshot.apiOnline ? "gb-ok" : "gb-bad"}`, children: [_jsx("span", {}), snapshot.apiOnline ? "Python agent online" : "Python agent offline"] })] }), _jsxs("section", { className: "gb-command", children: [_jsxs("button", { type: "button", onClick: () => updateFromCall("Refreshed", () => refresh.callToolAsync()), disabled: pending, children: [_jsx(RefreshCw, { size: 16 }), "Refresh"] }), _jsxs("button", { type: "button", className: "gb-primary", onClick: () => updateFromCall("Seeded demo completed", () => runDemo.callToolAsync()), disabled: pending, children: [_jsx(Play, { size: 16 }), "Run demo"] }), _jsxs("button", { type: "button", onClick: () => updateFromCall("Spike bid tested", () => bid.callToolAsync({
                            prompt: "Best CRM for a 50-person agency, pricing, demo, and enterprise trial.",
                            placement_id: "chatgpt-sponsored-answer-1",
                        })), disabled: pending, children: [_jsx(CircleDollarSign, { size: 16 }), "Test spike"] }), _jsxs("button", { type: "button", onClick: () => updateFromCall("Creative safety tested", () => creative.callToolAsync({
                            headline: "NorthstarCRM Guaranteed Growth",
                            body: "Guaranteed 3x revenue in 30 days with zero effort.",
                            claim: "Guaranteed 3x revenue in 30 days",
                        })), disabled: pending, children: [_jsx(FileCheck2, { size: 16 }), "Test creative"] }), _jsxs("button", { type: "button", onClick: () => updateFromCall("Waste policy tested", () => waste.callToolAsync({
                            placement_id: "chatgpt-sponsored-answer-1",
                            impressions: 640,
                            clicks: 42,
                            spend: 2.1,
                            revenue: 0.9,
                        })), disabled: pending, children: [_jsx(PauseCircle, { size: 16 }), "Test waste"] })] }), !snapshot.apiOnline ? (_jsxs("section", { className: "gb-alert", role: "alert", children: [_jsx(AlertTriangle, {}), _jsxs("div", { children: [_jsx("strong", { children: "Agent API unavailable" }), _jsx("p", { children: snapshot.error ?? "Start the FastAPI service on port 8000." })] })] })) : null, _jsxs("section", { className: "gb-metrics", children: [_jsx(Metric, { icon: _jsx(Gauge, {}), label: "Readiness", value: `${readiness}%`, tone: readiness >= 90 ? "good" : "warn" }), _jsx(Metric, { icon: _jsx(CircleDollarSign, {}), label: "Money escalations", value: flags.money_escalations ?? 0, tone: (flags.money_escalations ?? 0) > 0 ? "warn" : "neutral" }), _jsx(Metric, { icon: _jsx(ShieldCheck, {}), label: "Creative blocks", value: flags.creative_blocks ?? 0, tone: (flags.creative_blocks ?? 0) > 0 ? "bad" : "neutral" }), _jsx(Metric, { icon: _jsx(PauseCircle, {}), label: "Auto-pauses", value: flags.auto_paused_placements ?? 0, tone: (flags.auto_paused_placements ?? 0) > 0 ? "warn" : "neutral" })] }), _jsxs("section", { className: "gb-grid", children: [_jsx(Panel, { title: "Human boundary contracts", icon: _jsx(BadgeCheck, {}), children: _jsx("div", { className: "gb-contracts", children: contracts.map((contract) => (_jsxs("article", { className: contract.status === "FLAGGED" ? "gb-flagged" : "", children: [_jsxs("div", { children: [_jsx("strong", { children: contract.name }), _jsx("span", { children: contract.status })] }), _jsx("p", { children: contract.agent_can_act }), _jsx("small", { children: contract.human_boundary })] }, contract.name))) }) }), _jsxs(Panel, { title: "Sponsor surfaces", icon: _jsx(Sparkles, {}), children: [_jsxs("div", { className: "gb-sponsors", children: [_jsx(Sponsor, { label: "Overmind", value: snapshot.detail?.supervision?.enabled ? "tracing" : "local" }), _jsx(Sponsor, { label: "Alpic MCP", value: snapshot.detail?.mcp?.endpoint ?? "pending" }), _jsx(Sponsor, { label: "Skybridge", value: "interactive MCP app" }), _jsx(Sponsor, { label: "Tavily", value: "claim grounding visible in trace" })] }), _jsxs("p", { className: "gb-note", children: ["Last action: ", lastAction, ". Total spend $", Number(summary.total_spend ?? 0).toFixed(2), "; approvals ", summary.pending_approvals ?? approvals.filter((a) => a.status === "pending").length, "; traces ", summary.trace_count ?? 0, "."] })] })] }), _jsxs("section", { className: "gb-grid", children: [_jsx(Panel, { title: "Approval queue", icon: _jsx(AlertTriangle, {}), children: _jsx("div", { className: "gb-list", children: approvals.length ? (approvals.slice(0, 5).map((approval) => (_jsxs("article", { children: [_jsx("span", { children: approval.escalation_type }), _jsx("strong", { children: approval.reason }), _jsx("small", { children: approval.status })] }, approval.id)))) : (_jsx("p", { className: "gb-empty", children: "No approval items yet." })) }) }), _jsx(Panel, { title: "Latest policy hits", icon: _jsx(ShieldCheck, {}), children: _jsx("div", { className: "gb-timeline", children: events.length ? (events.slice(0, 7).map((event) => (_jsxs("article", { children: [_jsx("strong", { children: String(event.payload.policy ?? event.event_type) }), _jsx("span", { children: String(event.payload.outcome ?? event.message) })] }, event.id)))) : (_jsx("p", { className: "gb-empty", children: "Run the seeded demo to populate the trace." })) }) })] })] }));
}
function Metric({ icon, label, value, tone, }) {
    return (_jsxs("article", { className: `gb-metric gb-${tone}`, children: [_jsx("div", { children: icon }), _jsx("span", { children: label }), _jsx("strong", { children: value })] }));
}
function Panel({ title, icon, children, }) {
    return (_jsxs("section", { className: "gb-panel", children: [_jsxs("div", { className: "gb-panel-title", children: [icon, _jsx("h2", { children: title })] }), children] }));
}
function Sponsor({ label, value }) {
    return (_jsxs("div", { children: [_jsx("span", { children: label }), _jsx("strong", { children: value })] }));
}
//# sourceMappingURL=guardrail-console.js.map