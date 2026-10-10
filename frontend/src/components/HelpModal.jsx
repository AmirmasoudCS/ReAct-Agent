import Modal from "./Modal";
import "./HelpModal.css";

const TOOLS = [
  {
    name: "calculator",
    description: "Arithmetic.",
    example: "What is 15% of 2,340?",
  },
  {
    name: "wikipedia_search",
    description: "Encyclopedia facts about people, places and events.",
    example: "Who was Ada Lovelace?",
  },
  {
    name: "web_search",
    description: "Current information and recent events.",
    example: "What are the latest Python release notes?",
  },
  {
    name: "weather",
    description: "Current conditions and forecasts for up to 7 days.",
    example: "Weather in Berlin for the next three days",
  },
];

export default function HelpModal({ onClose }) {
  return (
    <Modal
      title="Help"
      onClose={onClose}
      footer={
        <>
          <span className="modal__footer-spacer" />
          <button
            type="button"
            className="modal-btn modal-btn--primary"
            onClick={onClose}
          >
            Close
          </button>
        </>
      }
    >
      <div className="help">
        <section>
          <h3>How the agent works</h3>
          <p>
            This is a ReAct agent. For each question it thinks about what it
            needs, picks a tool, reads the result, and repeats until it can
            give an answer. Simple questions and greetings are answered
            directly, without tools.
          </p>
        </section>

        <section>
          <h3>Tools it can use</h3>
          <ul className="help__tools">
            {TOOLS.map((tool) => (
              <li key={tool.name}>
                <code>{tool.name}</code>
                <span>{tool.description}</span>
                <em>Try: {tool.example}</em>
              </li>
            ))}
          </ul>
          <p>
            The activity panel under each answer shows which tools were used,
            with their inputs and results. Use the activity toggle in the
            header to show or hide it.
          </p>
        </section>

        <section>
          <h3>Chatting</h3>
          <ul>
            <li>
              Press <kbd>Enter</kbd> to send and <kbd>Shift</kbd> +{" "}
              <kbd>Enter</kbd> for a new line.
            </li>
            <li>
              The send button becomes a stop button while the agent is
              answering. Stopping keeps what has been written so far. A tool
              that is already running will still finish.
            </li>
            <li>
              Answers appear as they are written. Tool calls show up as soon
              as the agent makes them.
            </li>
          </ul>
        </section>

        <section>
          <h3>Conversations</h3>
          <ul>
            <li>
              Each conversation is saved. New ones are named automatically
              from your first message.
            </li>
            <li>
              Hover a conversation and open its <strong>...</strong> menu to
              rename or delete it. Deleting cannot be undone.
            </li>
            <li>The newest conversations are listed first.</li>
            <li>Use the search box to filter conversations by name.</li>
          </ul>
        </section>

        <section>
          <h3>Settings</h3>
          <p>
            Open Settings to choose the model, the temperature, and the
            maximum number of steps per question. Changes apply from your
            next message.
          </p>
        </section>

        <section>
          <h3>Good to know</h3>
          <ul>
            <li>The agent can make mistakes. Verify important information.</li>
            <li>
              If a tool fails or finds nothing, the agent may answer from its
              own knowledge and say that it is uncertain.
            </li>
          </ul>
        </section>
      </div>
    </Modal>
  );
}