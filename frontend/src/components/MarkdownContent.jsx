import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import CodeBlock from "./CodeBlock";
import "highlight.js/styles/github-dark.css";
import "./MarkdownContent.css";

const REMARK_PLUGINS = [remarkGfm];
const REHYPE_PLUGINS = [[rehypeHighlight, { ignoreMissing: true }]];

// Raw HTML in the text is NOT rendered (react-markdown's default), so model
// or tool output cannot inject markup into the page.
const COMPONENTS = {
  pre: CodeBlock,

  a: ({ node: _node, ...props }) => (
    <a {...props} target="_blank" rel="noopener noreferrer" />
  ),

  table: ({ node: _node, ...props }) => (
    <div className="markdown__table-wrap">
      <table {...props} />
    </div>
  ),
};

export default function MarkdownContent({ children }) {
  return (
    <div className="markdown">
      <ReactMarkdown
        remarkPlugins={REMARK_PLUGINS}
        rehypePlugins={REHYPE_PLUGINS}
        components={COMPONENTS}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}