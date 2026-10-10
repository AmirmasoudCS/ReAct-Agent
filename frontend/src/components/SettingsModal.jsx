import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import Modal from "./Modal";
import "./SettingsModal.css";

const FIELDS = ["model", "temperature", "max_steps"];

function isSame(a, b) {
  return FIELDS.every((field) => a[field] === b[field]);
}

/**
 * Agent settings: model, temperature and the step limit.
 * Render it only while it should be visible; it loads fresh values each
 * time it opens. Changes apply from the next message on.
 *
 * Needs api.getSettings(), api.updateSettings(changes), api.listModels().
 */
export default function SettingsModal({ api, onClose }) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const [saved, setSaved] = useState(null); // values stored on the server
  const [draft, setDraft] = useState(null); // values being edited
  const [defaults, setDefaults] = useState(null);
  const [limits, setLimits] = useState(null);
  const [models, setModels] = useState(null); // null: list unavailable

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [settings, modelList] = await Promise.all([
          api.getSettings(),
          // The model list is optional (Ollama may be unreachable).
          api.listModels().catch(() => null),
        ]);

        if (cancelled) return;

        setSaved(settings.values);
        setDraft(settings.values);
        setDefaults(settings.defaults);
        setLimits(settings.limits);
        setModels(modelList?.models ?? null);
      } catch (requestError) {
        if (!cancelled) {
          setError(requestError.message);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    load();

    return () => {
      cancelled = true;
    };
  }, [api]);

  const ready = !loading && draft !== null;
  const dirty = ready && !isSame(draft, saved);
  const atDefaults = ready && isSame(draft, defaults);

  function update(field, value) {
    setDraft((current) => ({ ...current, [field]: value }));
  }

  async function handleSave() {
    setSaving(true);
    setError("");

    try {
      await api.updateSettings(draft);
      onClose();
    } catch (requestError) {
      setError(requestError.message);
      setSaving(false);
    }
  }

  const modelOptions =
    ready && models
      ? models.includes(draft.model)
        ? models
        : [draft.model, ...models]
      : null;

  const footer = (
    <>
      <button
        type="button"
        className="modal-btn"
        onClick={() => setDraft(defaults)}
        disabled={!ready || atDefaults || saving}
      >
        Reset to defaults
      </button>

      <span className="modal__footer-spacer" />

      <button type="button" className="modal-btn" onClick={onClose}>
        Cancel
      </button>

      <button
        type="button"
        className="modal-btn modal-btn--primary"
        onClick={handleSave}
        disabled={!dirty || saving}
      >
        {saving ? "Saving..." : "Save"}
      </button>
    </>
  );

  return (
    <Modal title="Settings" onClose={onClose} footer={footer}>
      {loading && (
        <div className="settings__loading">
          <Loader2 className="settings__spinner" size={18} />
          <span>Loading settings...</span>
        </div>
      )}

      {error && (
        <p className="settings__error" role="alert">
          {error}
        </p>
      )}

      {ready && (
        <div className="settings">
          <div className="settings__field">
            <label htmlFor="setting-model">Model</label>

            {modelOptions ? (
              <select
                id="setting-model"
                value={draft.model}
                onChange={(event) => update("model", event.target.value)}
              >
                {modelOptions.map((name) => (
                  <option key={name} value={name}>
                    {name}
                  </option>
                ))}
              </select>
            ) : (
              <input id="setting-model" value={draft.model} disabled />
            )}

            <p className="settings__hint">
              {modelOptions
                ? "Models installed in Ollama."
                : "Could not load the installed models. Is Ollama running?"}
            </p>
          </div>

          <div className="settings__field">
            <div className="settings__label-row">
              <label htmlFor="setting-temperature">Temperature</label>
              <output htmlFor="setting-temperature">
                {draft.temperature.toFixed(2)}
              </output>
            </div>

            <input
              id="setting-temperature"
              type="range"
              min={limits.temperature.min}
              max={limits.temperature.max}
              step={limits.temperature.step}
              value={draft.temperature}
              onChange={(event) =>
                update("temperature", Number(event.target.value))
              }
            />

            <p className="settings__hint">
              Lower is more focused and consistent, which suits tool use.
              Higher is more varied.
            </p>
          </div>

          <div className="settings__field">
            <div className="settings__label-row">
              <label htmlFor="setting-steps">Maximum steps</label>
              <output htmlFor="setting-steps">{draft.max_steps}</output>
            </div>

            <input
              id="setting-steps"
              type="range"
              min={limits.max_steps.min}
              max={limits.max_steps.max}
              step={limits.max_steps.step}
              value={draft.max_steps}
              onChange={(event) =>
                update("max_steps", Number(event.target.value))
              }
            />

            <p className="settings__hint">
              How many reasoning and tool steps the agent may take for one
              question before it gives up.
            </p>
          </div>

          <p className="settings__note">
            Changes apply from your next message.
          </p>
        </div>
      )}
    </Modal>
  );
}