/** @vitest-environment jsdom */
import "@testing-library/jest-dom/vitest";
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import GlassCard from "../GlassCard";

describe("GlassCard", () => {
  it("renders children without crashing", () => {
    render(
      <GlassCard>
        <div>hello</div>
      </GlassCard>
    );

    expect(screen.getByText("hello")).toBeInTheDocument();
  });
});
