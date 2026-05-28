import { useToolInfo } from "@/helpers.js";
import { DecisionPanelView } from "./decision-panel.js";

export default function WasteDecisionPanel() {
  const toolInfo = useToolInfo<"evaluate_placement_waste">();
  return <DecisionPanelView toolInfo={toolInfo} defaultKind="waste" />;
}
