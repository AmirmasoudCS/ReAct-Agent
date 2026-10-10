import { useEffect, useRef, useState } from "react";
import { Check, Copy } from "lucide-react";
import "./CopyButton.css";

export default function CopyButton({
  text,
  label = "Copy",
  showLabel = false,
  className = "",
}) {
  const [copied, setCopied] = useState(false);
  const timer = useRef(null);

  useEffect(() => () => clearTimeout(timer.current), []);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      clearTimeout(timer.current);
      timer.current = setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard access can be denied; fail quietly.
    }
  }

  const currentLabel = copied ? "Copied" : label;

  return (
    <button
      type="button"
      className={`copy-button ${className}`}
      onClick={handleCopy}
      aria-label={currentLabel}
      title={currentLabel}
    >
      {copied ? <Check size={15} /> : <Copy size={15} />}
      {showLabel && <span>{currentLabel}</span>}
    </button>
  );
}