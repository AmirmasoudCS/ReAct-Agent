import { useRef, useState } from "react";
import {
  ArrowUp,
  FileText,
  Loader2,
  Paperclip,
  Square,
  X,
} from "lucide-react";
import "./ChatInput.css";

const ACCEPTED_TYPES = ".txt,.md,.pdf,.docx";

function formatSize(bytes = 0) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function describeDocument(document) {
  const parts = [formatSize(document.size_bytes)];

  if (document.pages) {
    parts.push(`${document.pages} ${document.pages === 1 ? "page" : "pages"}`);
  }

  parts.push(`${document.chunk_count} sections`);
  return `${document.name} (${parts.join(", ")})`;
}

/**
 * isBusy: the agent is answering. The send button turns into a stop
 * button, and sending is blocked (the typed text is kept).
 * disabled: the whole input is unavailable (no session, offline, loading).
 * documents / isUploading / onUpload / onRemoveDocument: attached files.
 * Attaching and removing are blocked while busy or uploading, because the
 * server locks the conversation during both.
 */
export default function ChatInput({
  onSend,
  onStop,
  isBusy = false,
  disabled = false,
  documents = [],
  isUploading = false,
  onUpload,
  onRemoveDocument,
}) {
  const [value, setValue] = useState("");
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);

  const attachBlocked = disabled || isBusy || isUploading || !onUpload;

  function handleSubmit(event) {
    event.preventDefault();

    const message = value.trim();

    if (!message || disabled || isBusy || isUploading) {
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

  function handleFilesChosen(event) {
    const files = Array.from(event.target.files ?? []);

    // Reset so choosing the same file again still fires onChange.
    event.target.value = "";

    if (files.length > 0 && !attachBlocked) {
      onUpload(files);
    }
  }

  const hasDocuments = documents.length > 0;

  return (
    <div className="chat-input-wrapper">
      <form className="chat-input" onSubmit={handleSubmit}>
        {hasDocuments && (
          <ul className="chat-input__files" aria-label="Attached documents">
            {documents.map((document) => (
              <li
                key={document.id}
                className="chat-input__file"
                title={describeDocument(document)}
              >
                <FileText size={14} aria-hidden="true" />
                <span className="chat-input__file-name">{document.name}</span>
                <button
                  type="button"
                  className="chat-input__file-remove"
                  onClick={() => onRemoveDocument?.(document.id)}
                  disabled={attachBlocked}
                  aria-label={`Remove ${document.name}`}
                  title="Remove document"
                >
                  <X size={13} />
                </button>
              </li>
            ))}
          </ul>
        )}

        <textarea
          ref={textareaRef}
          className="chat-input__textarea"
          value={value}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder={
            isUploading
              ? "Processing document..."
              : hasDocuments
                ? "Ask about your documents..."
                : "Message ReAct Agent..."
          }
          rows={1}
          disabled={disabled}
          aria-label="Message"
        />

        <div className="chat-input__toolbar">
          <input
            ref={fileInputRef}
            type="file"
            accept={ACCEPTED_TYPES}
            multiple
            hidden
            onChange={handleFilesChosen}
          />

          <button
            className="chat-input__attach"
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={attachBlocked}
            title={
              isUploading
                ? "Processing document..."
                : "Attach a document (.txt, .md, .pdf, .docx)"
            }
            aria-label="Attach a document"
          >
            {isUploading ? (
              <Loader2 className="chat-input__spinner" size={18} />
            ) : (
              <Paperclip size={18} />
            )}
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
              disabled={!value.trim() || disabled || isUploading}
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