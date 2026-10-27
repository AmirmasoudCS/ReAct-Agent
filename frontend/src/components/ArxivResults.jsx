import "./ArxivResults.css";

// Parses the arxiv_search observation:
//   header\n\n[1] Title\nAuthors: ...\nPublished: ... | Category: ...\nLink: ...\nAbstract: ...
export function parseArxivResults(text = "") {
  const chunks = text.split(/\n\n(?=\[\d+\] )/);
  const header = chunks[0].startsWith("[") ? "" : chunks.shift();

  const papers = chunks.map((chunk) => {
    const [first, ...rest] = chunk.split("\n");
    const paper = { title: first.replace(/^\[\d+\]\s*/, "") };

    for (const line of rest) {
      if (line.startsWith("Authors: ")) paper.authors = line.slice(9);
      else if (line.startsWith("Published: ")) paper.meta = line.slice(11);
      else if (line.startsWith("Link: ")) paper.link = line.slice(6).trim();
      else if (line.startsWith("Abstract: ")) paper.abstract = line.slice(10);
    }

    return paper;
  });

  return { header, papers };
}

// Only allow real arXiv links, never arbitrary URLs from tool output.
const isArxivLink = (url = "") => /^https:\/\/arxiv\.org\//.test(url);

export default function ArxivResults({ text }) {
  const { header, papers } = parseArxivResults(text);

  if (papers.length === 0) {
    return <pre>{text}</pre>;
  }

  return (
    <div className="arxiv">
      {header && <p className="arxiv__header">{header}</p>}
      <ol className="arxiv__list">
        {papers.map((paper, index) => (
          <li key={paper.link || index} className="arxiv__paper">
            {isArxivLink(paper.link) ? (
              <a href={paper.link} target="_blank" rel="noopener noreferrer">
                {paper.title}
              </a>
            ) : (
              <strong>{paper.title}</strong>
            )}
            {paper.authors && <p className="arxiv__authors">{paper.authors}</p>}
            {paper.meta && <p className="arxiv__meta">{paper.meta}</p>}
            {paper.abstract && <p className="arxiv__abstract">{paper.abstract}</p>}
          </li>
        ))}
      </ol>
    </div>
  );
}