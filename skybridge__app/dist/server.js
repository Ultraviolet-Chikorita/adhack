import { McpServer } from "skybridge/server";
import { z } from "zod";
const API_BASE = process.env.GUARDRAIL_API_BASE ?? "http://127.0.0.1:8000";
const DEFAULT_PLACEMENT = "chatgpt-sponsored-answer-1";
async function apiJson(path, init) {
    const response = await fetch(`${API_BASE}${path}`, {
        ...init,
        headers: {
            "content-type": "application/json",
            ...(init?.headers ?? {}),
        },
    });
    if (!response.ok) {
        const body = await response.text();
        throw new Error(`${path} failed with ${response.status}: ${body}`);
    }
    return (await response.json());
}
async function loadSnapshot(source, demo) {
    try {
        const [report, detail] = await Promise.all([
            apiJson("/policy/report"),
            apiJson("/state/detail"),
        ]);
        return {
            apiOnline: true,
            apiBase: API_BASE,
            generatedAt: new Date().toISOString(),
            source,
            report,
            detail,
            demo,
        };
    }
    catch (error) {
        return {
            apiOnline: false,
            apiBase: API_BASE,
            generatedAt: new Date().toISOString(),
            source,
            error: error instanceof Error ? error.message : String(error),
        };
    }
}
function textSummary(snapshot) {
    if (!snapshot.apiOnline) {
        return `GuardrailBidder API is offline at ${snapshot.apiBase}: ${snapshot.error}`;
    }
    const report = snapshot.report;
    const flags = report.flags ?? {};
    return [
        `GuardrailBidder readiness ${report.readiness_score ?? "unknown"}.`,
        `Money escalations: ${flags.money_escalations ?? 0}.`,
        `Creative blocks: ${flags.creative_blocks ?? 0}.`,
        `Auto-paused placements: ${flags.auto_paused_placements ?? 0}.`,
        `Policy hits: ${flags.policy_hits ?? 0}.`,
    ].join(" ");
}
const sharedViewConfig = {
    domain: "https://guardrailbidder.alpic.app",
    csp: {
        resourceDomains: ["https://fonts.googleapis.com", "https://fonts.gstatic.com"],
        redirectDomains: ["https://docs.skybridge.tech", "https://alpic.ai"],
    },
};
const server = new McpServer({
    name: "guardrailbidder-skybridge",
    version: "0.1.0",
}, { capabilities: {} })
    .registerTool({
    name: "show_guardrail_console",
    description: "Open an interactive GuardrailBidder dashboard view with policy flags, approvals, trace events, and sponsor integration status.",
    inputSchema: {},
    annotations: {
        title: "Show GuardrailBidder console",
        readOnlyHint: true,
        destructiveHint: false,
        openWorldHint: false,
    },
    _meta: {
        "openai/toolInvocation/invoking": "Loading GuardrailBidder console...",
        "openai/toolInvocation/invoked": "GuardrailBidder console ready.",
    },
    view: {
        ...sharedViewConfig,
        component: "guardrail-console",
        description: "GuardrailBidder human-in-the-loop control room",
    },
}, async () => {
    const snapshot = await loadSnapshot("status");
    return {
        structuredContent: snapshot,
        content: [{ type: "text", text: textSummary(snapshot) }],
        isError: !snapshot.apiOnline,
    };
})
    .registerTool({
    name: "run_guardrail_demo",
    description: "Run the seeded GuardrailBidder scenario: low intent skip, safe bid, spend spike escalation, off-brand creative block, Tavily claim check, and waste auto-pause.",
    inputSchema: {},
    annotations: {
        title: "Run seeded guardrail demo",
        readOnlyHint: false,
        destructiveHint: false,
        openWorldHint: false,
    },
    _meta: {
        "openai/toolInvocation/invoking": "Running the seeded guardrail demo...",
        "openai/toolInvocation/invoked": "Seeded guardrail demo complete.",
    },
    view: {
        ...sharedViewConfig,
        component: "guardrail-demo",
        description: "GuardrailBidder seeded governance demo",
    },
}, async () => {
    const demo = await apiJson("/demo/run", { method: "POST", body: "{}" });
    const snapshot = await loadSnapshot("demo", demo);
    return {
        structuredContent: snapshot,
        content: [{ type: "text", text: textSummary(snapshot) }],
        isError: !snapshot.apiOnline,
    };
})
    .registerTool({
    name: "evaluate_conversational_bid",
    description: "Score a conversational prompt, evaluate the bid, and show whether the agent can commit spend or must escalate.",
    inputSchema: {
        prompt: z.string().min(1).describe("Incoming conversational ad prompt."),
        placement_id: z
            .string()
            .optional()
            .describe("Placement id. Defaults to the ChatGPT-style sponsored answer slot."),
    },
    annotations: {
        title: "Evaluate bid guardrail",
        readOnlyHint: false,
        destructiveHint: false,
        openWorldHint: false,
    },
    _meta: {
        "openai/toolInvocation/invoking": "Evaluating bid guardrails...",
        "openai/toolInvocation/invoked": "Bid guardrail decision ready.",
    },
    view: {
        ...sharedViewConfig,
        component: "bid-decision-panel",
        description: "GuardrailBidder bid decision review",
    },
}, async ({ prompt, placement_id }) => {
    const result = await apiJson("/bid/evaluate", {
        method: "POST",
        body: JSON.stringify({ prompt, placement_id: placement_id ?? DEFAULT_PLACEMENT }),
    });
    const snapshot = await loadSnapshot("bid");
    return {
        structuredContent: { kind: "bid", result, snapshot },
        content: [{ type: "text", text: `Bid evaluated for: ${prompt}` }],
        isError: false,
    };
})
    .registerTool({
    name: "judge_inline_creative",
    description: "Judge proposed ad creative with the LLM-first safety judge, hard brand policy blocks, and Tavily-backed claim grounding.",
    inputSchema: {
        headline: z.string().min(1),
        body: z.string().min(1),
        claim: z.string().optional(),
    },
    annotations: {
        title: "Judge creative",
        readOnlyHint: false,
        destructiveHint: false,
        openWorldHint: true,
    },
    _meta: {
        "openai/toolInvocation/invoking": "Judging creative safety...",
        "openai/toolInvocation/invoked": "Creative judgement ready.",
    },
    view: {
        ...sharedViewConfig,
        component: "creative-decision-panel",
        description: "GuardrailBidder creative safety decision review",
    },
}, async ({ headline, body, claim }) => {
    const result = await apiJson("/creative/judge-inline", {
        method: "POST",
        body: JSON.stringify({ headline, body, claim }),
    });
    const snapshot = await loadSnapshot("creative");
    return {
        structuredContent: { kind: "creative", result, snapshot },
        content: [{ type: "text", text: `Creative judged: ${headline}` }],
        isError: false,
    };
})
    .registerTool({
    name: "evaluate_placement_waste",
    description: "Upsert placement metrics, evaluate ROAS/CPA waste policy, and auto-pause clear losers with traceable rationale.",
    inputSchema: {
        placement_id: z.string().optional(),
        impressions: z.number().int().nonnegative(),
        clicks: z.number().int().nonnegative(),
        spend: z.number().nonnegative(),
        revenue: z.number().nonnegative(),
    },
    annotations: {
        title: "Evaluate waste guardrail",
        readOnlyHint: false,
        destructiveHint: false,
        openWorldHint: false,
    },
    _meta: {
        "openai/toolInvocation/invoking": "Evaluating placement waste...",
        "openai/toolInvocation/invoked": "Waste decision ready.",
    },
    view: {
        ...sharedViewConfig,
        component: "waste-decision-panel",
        description: "GuardrailBidder waste decision review",
    },
}, async ({ placement_id, impressions, clicks, spend, revenue }) => {
    const id = placement_id ?? DEFAULT_PLACEMENT;
    await apiJson("/placements/upsert", {
        method: "POST",
        body: JSON.stringify({
            placement_id: id,
            impressions,
            clicks,
            spend,
            revenue,
            paused: false,
            pause_reason: null,
        }),
    });
    const result = await apiJson(`/placements/evaluate-waste/${id}`, {
        method: "POST",
        body: "{}",
    });
    const snapshot = await loadSnapshot("waste");
    return {
        structuredContent: { kind: "waste", result, snapshot },
        content: [{ type: "text", text: `Waste evaluated for placement ${id}` }],
        isError: false,
    };
});
server.express.get("/health", (_req, res) => {
    res.json({ status: "ok", apiBase: API_BASE });
});
if (process.env.NODE_ENV === "production") {
    const { default: manifest } = await import("./vite-manifest.js");
    server.setViteManifest(manifest);
}
export default await server.run();
//# sourceMappingURL=server.js.map