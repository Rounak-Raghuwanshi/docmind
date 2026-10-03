import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { confirmDialog, promptDialog } from "@/stores/dialog";
import { DialogHost } from "./DialogHost";

describe("DialogHost", () => {
  it("resolves confirmDialog with true on confirm", async () => {
    render(<DialogHost />);
    let result: Promise<boolean>;
    act(() => {
      result = confirmDialog({ title: "Delete it?", confirmText: "Delete", tone: "danger" });
    });
    expect(await screen.findByRole("alertdialog", { name: "Delete it?" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Delete" }));
    await expect(result!).resolves.toBe(true);
  });

  it("resolves false on Escape", async () => {
    render(<DialogHost />);
    let result: Promise<boolean>;
    act(() => {
      result = confirmDialog({ title: "Leave?" });
    });
    await screen.findByRole("alertdialog");
    await userEvent.keyboard("{Escape}");
    await expect(result!).resolves.toBe(false);
  });

  it("promptDialog returns the typed text, or null when cancelled", async () => {
    render(<DialogHost />);
    let typed: Promise<string | null>;
    act(() => {
      typed = promptDialog({ title: "What was wrong?", confirmText: "Send" });
    });
    await userEvent.type(await screen.findByRole("textbox"), "Missed the limit");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));
    await expect(typed!).resolves.toBe("Missed the limit");

    let cancelled: Promise<string | null>;
    act(() => {
      cancelled = promptDialog({ title: "Again?" });
    });
    await userEvent.click(await screen.findByRole("button", { name: "Cancel" }));
    await expect(cancelled!).resolves.toBeNull();
  });
});
