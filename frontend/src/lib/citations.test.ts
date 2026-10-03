import { describe, expect, it } from "vitest";
import type { Citation } from "@/api/types";
import { formatPages, linkCitations } from "./citations";
import { shouldHighlight, normaliseForMatch } from "./highlight";
import { validateFile } from "./uploads";

const cite = (n: number): Citation => ({
  n,
  chunk_id: `c${n}`,
  document_id: "d",
  filename: "f.pdf",
  page: n,
  snippet: "s",
});

describe("linkCitations", () => {
  it("links valid markers and drops invented ones", () => {
    expect(linkCitations("A [1]. B [2][9].", [cite(1), cite(2)])).toBe(
      "A [1](cite:1). B [2](cite:2).",
    );
  });
  it("leaves markers untouched while streaming (citations unknown)", () => {
    expect(linkCitations("A [1]", null)).toBe("A [1]");
  });
  it("does not touch existing markdown links", () => {
    expect(linkCitations("[1](http://x)", [cite(1)])).toBe("[1](http://x)");
  });
});

describe("formatPages", () => {
  it("formats single pages and ranges", () => {
    expect(formatPages({ page: 4 })).toBe("p. 4");
    expect(formatPages({ page: 4, page_end: 6 })).toBe("pp. 4–6");
  });
});

describe("highlight matching", () => {
  const snippet = normaliseForMatch(
    "Section 80D allows a deduction for health insurance premiums paid by the taxpayer.",
  );
  it("matches lines inside the snippet", () => {
    expect(shouldHighlight("allows a deduction for health", snippet)).toBe(true);
    expect(shouldHighlight("Completely unrelated text here", snippet)).toBe(false);
    expect(shouldHighlight("80D", snippet)).toBe(false); // too short to be meaningful
    expect(shouldHighlight("health insurance", snippet)).toBe(true);
    expect(shouldHighlight("₹50,000", normaliseForMatch("limit is ₹50,000 for parents"))).toBe(
      false,
    );
  });
});

describe("validateFile", () => {
  const file = (name: string, size: number) => new File([new Uint8Array(size)], name);
  it("accepts supported types within the limit", () => {
    expect(validateFile(file("a.pdf", 10))).toBeNull();
    expect(validateFile(file("Notes.MD", 10))).toBeNull();
  });
  it("rejects unsupported, empty and oversized files", () => {
    expect(validateFile(file("a.exe", 10))).toMatch(/Unsupported/);
    expect(validateFile(file("a.pdf", 0))).toMatch(/empty/);
    expect(validateFile(file("a.pdf", 2 * 1024 * 1024), 1)).toMatch(/Larger than 1 MB/);
  });
});
