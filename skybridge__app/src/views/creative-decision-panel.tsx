import { useToolInfo } from "@/helpers.js";
import { DecisionPanelView } from "./decision-panel.js";

export default function CreativeDecisionPanel() {
  const toolInfo = useToolInfo<"judge_inline_creative">();
  return <DecisionPanelView toolInfo={toolInfo} defaultKind="creative" />;
}
