import "./DocumentResults.css";

// Parses the document_search observation:
//   header\n\n[1] name (page 2, excerpt 3 of 9)\ntext\n\n[2] ...\n\nNote: ...
export function parseDocumentResults(text = "") {
  const noteIndex = text.lastIndexOf("\n\nNote: ");
  const body = noteIndex === -1 ? text : text.slice(0, noteIndex);
  const note = noteIndex === -1 ? "" : text.slice(noteIndex + 2);

  const chunks = body.split(
    /\n\n(?=\[\d+\] .+ \([^()\n]*excerpt \d+ of \d+\)\n)/,
  );
  const header = chunks[0].startsWith("[") ? "" : chunks.shift();

  const excerpts = [];

  for (const chunk of chunks) {
    const [first, ...rest] = chunk.split("\n");
    const match = first.match(
      /^\[(\d+)\] (.+) \(([^()\n]*excerpt \d+ of \d+)\)$/,
    );

    if (match) {
      excerpts.push({
        number: match[1],
        name: match[2],
        meta: match[3],
        text: rest.join("\n").trim(),
      });
    }
  }

  return { header, note, excerpts };
}

// Falls back to the raw text for anything that does not parse (errors,
// "No relevant excerpts found", and so on).
export default function DocumentResults({ text }) {
  const { header, note, excerpts } = parseDocumentResults(text);

  if (excerpts.length === 0) {
    return <pre>{text}</pre>;
  }

  return (
    <div className="docresults">
      {header && <p className="docresults__header">{header}</p>}
      <ol className="docresults__list">
        {excerpts.map((excerpt) => (
          <li key={excerpt.number} className="docresults__excerpt">
            <p className="docresults__title">
              <strong>{excerpt.name}</strong>
              <span>{excerpt.meta}</span>
            </p>
            <p className="docresults__text">{excerpt.text}</p>
          </li>
        ))}
      </ol>
      {note && <p className="docresults__note">{note}</p>}
    </div>
  );
}