import { BookOpen, Calculator, CloudSun, Globe, Wrench } from "lucide-react";

// First matching rule wins. Add a line when you add a tool.
const ICON_RULES = [
  [/calc|math/i, Calculator],
  [/weather/i, CloudSun],
  [/wiki/i, BookOpen],
  [/search|web/i, Globe],
];

export function getToolIcon(toolName = "") {
  for (const [pattern, Icon] of ICON_RULES) {
    if (pattern.test(toolName)) return Icon;
  }
  return Wrench;
}