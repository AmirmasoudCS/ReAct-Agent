import {
  BookOpen,
  Calculator,
  Clock,
  CloudSun,
  FileSearch,
  FileText,
  Globe,
  Wrench,
} from "lucide-react";

// First matching rule wins. Add a line when you add a tool.
// "document" must stay above "search|web", which would match document_search.
const ICON_RULES = [
  [/calc|math/i, Calculator],
  [/weather/i, CloudSun],
  [/date|time|clock/i, Clock],
  [/wiki/i, BookOpen],
  [/document/i, FileSearch],
  [/arxiv|paper/i, FileText],
  [/search|web/i, Globe],
];

export function getToolIcon(toolName = "") {
  for (const [pattern, Icon] of ICON_RULES) {
    if (pattern.test(toolName)) return Icon;
  }
  return Wrench;
}