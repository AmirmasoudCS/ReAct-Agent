import { useState } from "react";
import { ChevronRight, TriangleAlert } from "lucide-react";
import { groupActivity } from "../utils/activity";
import { getToolIcon } from "./toolMeta";
import "./ActivityPanel.css";

function ToolStep({ step, renderResult }) {
  const [open, setOpen] = useState(false);
  const Icon = getToolIcon(step.toolName);
  const hasResult = step.result !== null;
  const isError = step.status === "error";

  return (
    <li className={`activity__step ${isError ? "activity__step--error" : ""}`}>
      <button
        type="button"
        className="activity__step-header"
        onClick={() => setOpen((current) => !current)}
        aria-expanded={hasResult ? open : undefined}
        disabled={!hasResult}
        title={hasResult ? "Show result" : "No result recorded"}
      >
        <span className="activity__icon">
          <Icon size={15} />
        </span>
        <span className="activity__tool">{step.toolName}</span>
        <code className="activity__input">{step.toolInput}</code>

        {isError && (
          <span className="activity__flag" title="The tool returned an error">
            <TriangleAlert size={15} aria-label="Error" />
          </span>
        )}

        {hasResult && <ChevronRight className="activity__chevron" size={15} />}
      </button>

      {open && hasResult && (
        <div className="activity__result">
          {renderResult ? renderResult(step) : <pre>{step.result}</pre>}
        </div>
      )}
    </li>
  );
}

/**
 * Shows the tools the agent used for one answer.
 *
 * toolRenderers: optional map of lowercase tool name -> (step) => node,
 * e.g. { weather: (step) => <WeatherCard text={step.result} /> }.
 * Tools without an entry fall back to the raw result text.
 */
export default function ActivityPanel({ activity, toolRenderers }) {
  const steps = groupActivity(activity);

  if (steps.length === 0) {
    return null;
  }

  return (
    <section className="activity" aria-label="Agent activity">
      <p className="activity__heading">
        Used {steps.length} {steps.length === 1 ? "tool" : "tools"}
      </p>

      <ul className="activity__steps">
        {steps.map((step) => (
          <ToolStep
            key={step.id}
            step={step}
            renderResult={toolRenderers?.[step.toolName.toLowerCase()]}
          />
        ))}
      </ul>
    </section>
  );
}