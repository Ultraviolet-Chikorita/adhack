import { z } from "zod";

/** Mirrors guardrailbidder FastAPI /policy/report flags and risk score. */
export const policyFlagsSchema = z.object({
  money_escalations: z.number().optional(),
  creative_blocks: z.number().optional(),
  auto_paused_placements: z.number().optional(),
  policy_hits: z.number().optional(),
});

export const policyReportSchema = z.object({
  risk_score: z.number().optional(),
  readiness_score: z.number().optional(),
  flags: policyFlagsSchema.optional(),
  contracts: z
    .array(
      z.object({
        name: z.string(),
        agent_can_act: z.string(),
        human_boundary: z.string(),
        status: z.string(),
      }),
    )
    .optional(),
  latest_policy_events: z
    .array(
      z.object({
        id: z.string(),
        event_type: z.string(),
        message: z.string(),
        payload: z.record(z.string(), z.unknown()),
        created_at: z.string(),
      }),
    )
    .optional(),
});

export const stateSummarySchema = z.object({
  total_spend: z.number().optional(),
  bid_count: z.number().optional(),
  creative_count: z.number().optional(),
  pending_approvals: z.number().optional(),
  trace_count: z.number().optional(),
});

export const guardrailSnapshotSchema = z.object({
  apiOnline: z.boolean(),
  apiBase: z.string(),
  generatedAt: z.string(),
  source: z.string(),
  report: policyReportSchema.optional(),
  detail: z
    .object({
      summary: stateSummarySchema.optional(),
      approvals: z
        .array(
          z.object({
            id: z.string(),
            escalation_type: z.string(),
            reason: z.string(),
            status: z.string(),
          }),
        )
        .optional(),
      supervision: z
        .object({
          enabled: z.boolean().optional(),
          service_name: z.string().optional(),
          environment: z.string().optional(),
        })
        .optional(),
      mcp: z
        .object({
          endpoint: z.string().optional(),
          tools: z.number().optional(),
          transport: z.string().optional(),
        })
        .optional(),
    })
    .optional(),
  demo: z.unknown().optional(),
  error: z.string().optional(),
});

export const decisionOutputSchema = z.object({
  kind: z.enum(["bid", "creative", "waste"]).optional(),
  result: z.record(z.string(), z.unknown()).optional(),
  snapshot: guardrailSnapshotSchema.optional(),
});

export type PolicyReport = z.infer<typeof policyReportSchema>;
export type GuardrailSnapshot = z.infer<typeof guardrailSnapshotSchema>;
export type DecisionOutput = z.infer<typeof decisionOutputSchema>;

export function policyRiskScore(report: PolicyReport | undefined): number {
  if (!report) {
    return 0;
  }
  return report.risk_score ?? report.readiness_score ?? 0;
}
