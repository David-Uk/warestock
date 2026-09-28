import { describe, expect, it } from "vitest";
import { capitalize, cn, formatPercent, formatQty, formatDate, truncate } from "./utils";

describe("cn", () => {
  it("merges class names and resolves conflicts", () => {
    expect(cn("p-2", "p-4")).toBe("p-4");
    const oversized: boolean = false;
    expect(cn("text-sm", oversized && "text-lg", "font-bold")).toBe("text-sm font-bold");
  });

  it("keeps custom text-scale sizes alongside color classes", () => {
    expect(cn("text-white", "text-body-lg")).toBe("text-white text-body-lg");
    expect(cn("text-primary-container", "text-body-md", "text-white")).toBe(
      "text-body-md text-white"
    );
    expect(cn("text-body-lg", "text-body-md")).toBe("text-body-md");
    expect(cn("md:text-body-sm", "text-white")).toBe("md:text-body-sm text-white");
  });
});

describe("formatQty", () => {
  it("groups thousands", () => {
    expect(formatQty(12480)).toBe("12,480");
    expect(formatQty(0)).toBe("0");
  });
});

describe("formatPercent", () => {
  it("rounds a ratio to a whole percent", () => {
    expect(formatPercent(0.826)).toBe("83%");
    expect(formatPercent(1)).toBe("100%");
  });
});

describe("formatDate", () => {
  it("formats ISO strings and Date objects", () => {
    expect(formatDate("2026-09-28")).toMatch(/28 Sep(t)? 2026/);
    expect(formatDate(new Date(2026, 0, 5))).toMatch(/05 Jan 2026/);
  });
});

describe("capitalize", () => {
  it("uppercases the first character", () => {
    expect(capitalize("reconciled")).toBe("Reconciled");
    expect(capitalize("")).toBe("");
  });
});

describe("truncate", () => {
  it("leaves short values alone and elides long ones", () => {
    expect(truncate("SKU-1", 10)).toBe("SKU-1");
    expect(truncate("SKU-48291-BULK", 8)).toBe("SKU-482…");
  });
});
