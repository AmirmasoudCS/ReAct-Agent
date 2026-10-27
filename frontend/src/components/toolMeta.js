import { BookOpen, Calculator, Clock, CloudSun, FileText, Globe, Wrench } from "lucide-react";

// First matching rule wins. Add a line when you add a tool.
const ICON_RULES = [
  [/calc|math/i, Calculator],
  [/weather/i, CloudSun],
  [/date|time|clock/i, Clock],
  [/wiki/i, BookOpen],
  [/arxiv|paper/i, FileText],
  [/search|web/i, Globe],
];

export function getToolIcon(toolName = "") {
  for (const [pattern, Icon] of ICON_RULES) {
    if (pattern.test(toolName)) return Icon;
  }
  return Wrench;
}