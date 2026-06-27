/** Decode Greenhouse-style entity-encoded HTML for display. */
export function decodeJobHtml(html: string): string {
  if (typeof document !== "undefined") {
    const el = document.createElement("textarea");
    el.innerHTML = html;
    return el.value;
  }
  return html
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&amp;/g, "&")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&nbsp;/g, " ");
}

/** Strip tags for preview snippets in job cards. */
export function plainTextFromHtml(html: string, maxLen = 120): string {
  const decoded = decodeJobHtml(html);
  const plain = decoded.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
  return plain.length > maxLen ? `${plain.slice(0, maxLen)}…` : plain;
}
