import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import "@/index.css";
import { AlertTriangle, BadgeCheck, CircleDollarSign, PauseCircle, ShieldCheck, } from "lucide-react";
import { useToolInfo } from "@/helpers.js";
export default function DecisionPanel() {
    const toolInfo = useToolInfo();
    const output = toolInfo.isSuccess
        ? toolInfo.output
        : undefined;
    const kind = output?.kind ?? "bid";
    const result = output?.result ?? {};
    const title = kind === "creative"
        ? "Creative judgement"
        : kind === "waste"
            ? "Waste decision"
            : "Bid decision";
    const icon = kind === "creative" ? (_jsx(ShieldCheck, {})) : kind === "waste" ? (_jsx(PauseCircle, {})) : (_jsx(CircleDollarSign, {}));
    return (_jsxs("main", { className: "gb-shell gb-compact", "data-llm": decisionSummary(kind, result), children: [_jsxs("header", { className: "gb-header", children: [_jsxs("div", { children: [_jsx("p", { className: "gb-eyebrow", children: "GuardrailBidder \u00B7 Skybridge App" }), _jsx("h1", { children: title })] }), _jsxs("div", { className: "gb-live gb-ok", children: [_jsx("span", {}), "Tool-backed review"] })] }), _jsxs("section", { className: "gb-decision", children: [_jsx("div", { className: "gb-decision-icon", children: icon }), _jsxs("div", { children: [_jsx("p", { className: "gb-eyebrow", children: kind }), _jsx("h2", { children: decisionHeadline(kind, result) }), _jsx("p", { children: decisionReason(kind, result) })] })] }), _jsxs("section", { className: "gb-json-grid", children: [_jsx(JsonBlock, { title: "Tool result", value: result }), _jsx(JsonBlock, { title: "Current policy posture", value: {
                            readiness: output?.snapshot?.report?.readiness_score,
                            flags: output?.snapshot?.report?.flags,
                        } })] }), _jsxs("section", { className: "gb-handoff", children: [_jsx(AlertTriangle, {}), _jsxs("p", { children: ["The model receives this structured decision and the view exposes the same state through ", _jsx("code", { children: "data-llm" }), ", so follow-up questions stay grounded in the actual guardrail outcome."] })] })] }));
}
function decisionHeadline(kind, result) {
    if (kind === "creative") {
        const judgement = result.judgement;
        return `Verdict: ${String(judgement?.verdict ?? "unknown")}`;
    }
    if (kind === "waste") {
        return Boolean(result.auto_paused) ? "Placement auto-paused" : "Placement still active";
    }
    const bid = result.bid;
    if (!bid) {
        return "Awaiting bid result";
    }
    return Boolean(bid.requires_human)
        ? "Human approval required"
        : Boolean(bid.approved)
            ? "Agent may commit spend"
            : "Agent did not bid";
}
function decisionReason(kind, result) {
    if (kind === "creative") {
        const judgement = result.judgement;
        const source = judgement?.source_url ? ` Source: ${String(judgement.source_url)}` : "";
        return `${String(judgement?.reason ?? "No reason returned.")}${source}`;
    }
    if (kind === "waste") {
        return String(result.message ?? "No waste message returned.");
    }
    const bid = result.bid;
    const intent = result.intent;
    return `Intent ${String(intent?.score ?? "unknown")} from ${String(intent?.source ?? "unknown")}. ${String(bid?.reason ?? "No bid reason returned.")}`;
}
function decisionSummary(kind, result) {
    return `${kind} decision: ${decisionHeadline(kind, result)}. ${decisionReason(kind, result)}`;
}
function JsonBlock({ title, value }) {
    return (_jsxs("article", { className: "gb-json", children: [_jsxs("div", { children: [_jsx(BadgeCheck, { size: 16 }), _jsx("strong", { children: title })] }), _jsx("pre", { children: JSON.stringify(value, null, 2) })] }));
}
//# sourceMappingURL=decision-panel.js.map