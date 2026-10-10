import "./ActivityPanel.css";
// Renders the agent's steps (planning / tool call / tool result).
// Add or override a renderer per activity type via the `renderers` prop,
// e.g. to show a weather card for a "Weather" tool call.

const DEFAULT_RENDERERS = {
  planning: (item) => (
    <>
      <span className="message-activity__label">Planning</span>
      <p>{item.content}</p>
    </>
  ),

  action: (item) => (
    <>
      <span className="message-activity__label">Tool call</span>
      <p className="message-activity__tool">{item.tool_name}</p>
      {item.tool_input && (
        <pre className="message-activity__code">{item.tool_input}</pre>
      )}
    </>
  ),

  observation: (item) => (
    <>
      <span className="message-activity__label">Tool result</span>
      <pre className="message-activity__code">{item.content}</pre>
    </>
  ),
};

function renderFallback(item) {
  return <pre className="message-activity__code">{JSON.stringify(item)}</pre>;
}

export default function ActivityPanel({
  activity,
  heading = "Agent activity",
  renderers,
}) {
  if (!activity?.length) {
    return null;
  }

  const allRenderers = { ...DEFAULT_RENDERERS, ...renderers };

  return (
    <div className="message-activity">
      <div className="message-activity__heading">{heading}</div>

      <div className="message-activity__items">
        {activity.map((item, index) => (
          <div
            className={`message-activity__item message-activity__item--${item.type}`}
            key={`${item.type}-${index}`}
          >
            <span className="message-activity__marker" />

            <div className="message-activity__body">
              {(allRenderers[item.type] ?? renderFallback)(item)}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}