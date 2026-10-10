import { Children, isValidElement } from "react";
import CopyButton from "./CopyButton";

function extractText(node) {
  if (node == null || typeof node === "boolean") return "";
  if (typeof node === "string" || typeof node === "number") return String(node);
  if (Array.isArray(node)) return node.map(extractText).join("");
  if (isValidElement(node)) return extractText(node.props.children);
  return "";
}

// Receives the <pre> element from react-markdown. Its child is the <code>
// element, which carries the "language-xxx" class and the highlighted spans.
export default function CodeBlock({ children }) {
  const codeElement = Children.toArray(children).find(isValidElement);
  const className = codeElement?.props?.className ?? "";
  const language = /language-([\w+#-]+)/.exec(className)?.[1];
  const text = extractText(children).replace(/\n$/, "");

  return (
    <div className="code-block">
      <div className="code-block__header">
        <span>{language ?? "text"}</span>
        <CopyButton text={text} label="Copy code" showLabel />
      </div>
      <pre>{children}</pre>
    </div>
  );
}