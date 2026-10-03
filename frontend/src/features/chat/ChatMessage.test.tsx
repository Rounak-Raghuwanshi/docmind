import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { useUi } from "@/stores/ui";
import { ChatMessage, type DisplayMessage } from "./ChatMessage";

const citation = {
  n: 1,
  chunk_id: "c1",
  document_id: "d1",
  filename: "Income-Tax-Act.pdf",
  page: 412,
  snippet: "Section 80D allows a deduction",
};

function renderMessage(message: DisplayMessage, streaming = false) {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <ChatMessage message={message} conversationId="conv" streaming={streaming} />
    </QueryClientProvider>,
  );
}

const base: DisplayMessage = {
  id: "m1",
  role: "assistant",
  content: "The limit is ₹25,000 [1]. Invented claim [7].",
  citations: [citation],
  status: "complete",
  not_found: false,
  cached: false,
  total_ms: 1200,
};

describe("ChatMessage", () => {
  it("renders citation chips for valid markers only", () => {
    renderMessage(base);
    const chips = screen.getAllByRole("button", { name: /Source 1: Income-Tax-Act.pdf, p. 412/ });
    expect(chips).toHaveLength(2); // inline chip + source list chip
    expect(screen.queryByText("[7]")).not.toBeInTheDocument();
    expect(screen.queryByText(/7/)).not.toBeInTheDocument();
  });

  it("opens the cited page when a chip is clicked", async () => {
    renderMessage(base);
    await userEvent.click(screen.getAllByRole("button", { name: /Source 1/ })[0]!);
    expect(useUi.getState().activeCitation?.page).toBe(412);
    expect(useUi.getState().viewerDocumentId).toBe("d1");
  });

  it("shows a searching indicator before the first token", () => {
    renderMessage({ ...base, id: null, content: "", citations: null }, true);
    expect(screen.getByText(/Searching your documents/)).toBeInTheDocument();
  });

  it("shows feedback and sources controls on completed answers", () => {
    renderMessage(base);
    expect(screen.getByRole("button", { name: "Helpful" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Show sources/ })).toBeInTheDocument();
  });
});
