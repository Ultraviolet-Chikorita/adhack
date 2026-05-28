import { useToolInfo } from "@/helpers.js";
import { DecisionPanelView } from "./decision-panel.js";

export default function BidDecisionPanel() {
  const toolInfo = useToolInfo<"evaluate_conversational_bid">();
  return <DecisionPanelView toolInfo={toolInfo} defaultKind="bid" />;
}
