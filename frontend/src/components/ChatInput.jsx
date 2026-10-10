import { useRef, useState } from "react";
import { ArrowUp, Paperclip, Square } from "lucide-react";
import "./ChatInput.css";

/**
 * isBusy: the agent is answering. The send button turns into a stop
 * button, and sending is blocked (the typed text is kept).
 * disabled: the whole input is unavailable (no session, offline, loading).
 */
export default function ChatInput({
  onSend,
  onStop,
  isBusy = false,
  disabled = false,
}) {
  const [value, setValue] = useState("");
  const textareaRef = useRef(null);

  function handleSubmit(event) {
    event.preventDefault();

    const message = value.trim();

    if (!message || disabled || isBusy) {
      return;
    }

    onSend(message);
    setValue("");

    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }

  function handleKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  }

  function handleChange(event) {
    setValue(event.target.value);

    const textarea = event.target;
    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
  }

  return (
    <div className="chat-input-wrapper">
      <form className="chat-input" onSubmit={handleSubmit}>
        <textarea
          ref={textareaRef}
          className="chat-input__textarea"
          value={value}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder="Message ReAct Agent..."
          rows={1}
          disabled={disabled}
          aria-label="Message"
        />

        <div className="chat-input__toolbar">
          <button
            className="chat-input__attach"
            type="button"
            disabled
            title="Attachments are not implemented yet"
            aria-label="Attachments unavailable"
          >
            <Paperclip size={18} />
          </button>

          {isBusy ? (
            <button
              className="chat-input__stop"
              type="button"
              onClick={onStop}
              aria-label="Stop response"
              title="Stop response"
            >
              <Square size={14} fill="currentColor" />
            </button>
          ) : (
            <button
              className="chat-input__send"
              type="submit"
              disabled={!value.trim() || disabled}
              aria-label="Send message"
              title="Send message"
            >
              <ArrowUp size={19} />
            </button>
          )}
        </div>
      </form>

      <p className="chat-input__disclaimer">
        ReAct Agent can make mistakes. Verify important information.
      </p>
    </div>
  );
}