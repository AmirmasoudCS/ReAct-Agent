// Turns the backend's flat activity list into one step per tool call:
//
//   [planning, action, observation, planning, action, observation]
//     -> [{ toolName, toolInput, result, status }, { ... }]
//
// "planning" items carry no information (the backend hides the model's
// thoughts on purpose), so they are dropped.

export function groupActivity(activity = []) {
  const steps = [];
  let current = null;

  for (const item of activity) {
    if (item.type === "action") {
      current = {
        id: `tool-${steps.length}`,
        toolName: item.tool_name || "Tool",
        toolInput: item.tool_input ?? "",
        result: null,
        status: "pending",
      };
      steps.push(current);
    } else if (item.type === "observation") {
      const status = /^error\b/i.test(item.content) ? "error" : "done";

      if (current && current.result === null) {
        current.result = item.content;
        current.status = status;
      } else {
        steps.push({
          id: `tool-${steps.length}`,
          toolName: "Tool",
          toolInput: "",
          result: item.content,
          status,
        });
      }

      current = null;
    }
  }

  return steps;
}