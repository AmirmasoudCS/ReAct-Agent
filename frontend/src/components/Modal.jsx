import { useEffect, useRef } from "react";
import { X } from "lucide-react";
import "./Modal.css";

/**
 * A centered dialog. Render it only while it should be visible.
 * Closes on Escape, on the X button, or on a click outside the dialog.
 * footer: optional content for the bottom bar (buttons).
 */
export default function Modal({ title, onClose, footer, children }) {
  const dialogRef = useRef(null);
  const onCloseRef = useRef(onClose);

  // Keep the latest onClose without re-running the focus effect below,
  // which would pull focus out of inputs on every re-render.
  useEffect(() => {
    onCloseRef.current = onClose;
  });

  useEffect(() => {
    const previouslyFocused = document.activeElement;

    dialogRef.current?.focus();

    function handleKeyDown(event) {
      if (event.key === "Escape") {
        onCloseRef.current?.();
      }
    }

    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      previouslyFocused?.focus?.();
    };
  }, []);

  return (
    <div
      className="modal-overlay"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          onClose();
        }
      }}
    >
      <div
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        tabIndex={-1}
        ref={dialogRef}
      >
        <header className="modal__header">
          <h2 id="modal-title">{title}</h2>

          <button
            type="button"
            className="modal__close"
            onClick={onClose}
            aria-label="Close"
          >
            <X size={18} />
          </button>
        </header>

        <div className="modal__body">{children}</div>

        {footer && <footer className="modal__footer">{footer}</footer>}
      </div>
    </div>
  );
}