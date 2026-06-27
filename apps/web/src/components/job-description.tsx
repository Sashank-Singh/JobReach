"use client";

import { decodeJobHtml } from "@/lib/job-html";

interface Props {
  html: string;
}

/** Renders decoded job description HTML with readable typography. */
export function JobDescription({ html }: Props) {
  const decoded = decodeJobHtml(html);

  return (
    <div
      className="job-description"
      dangerouslySetInnerHTML={{ __html: decoded }}
    />
  );
}
