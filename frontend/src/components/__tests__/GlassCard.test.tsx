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

  it("applies default tone and padding classes", () => {
    render(
      <GlassCard>
        <span data-testid="inner" />
      </GlassCard>
    );

    const wrapper = screen.getByTestId("glass-card");
    expect(wrapper).toHaveClass("rounded-2xl");
    expect(wrapper).toHaveClass("bg-white/10");
    expect(wrapper).toHaveClass("text-white");

    const inner = screen.getByTestId("inner").parentElement as HTMLElement;
    expect(inner).toHaveClass("p-4");
  });

  const toneClassMap: Record<string, string[]> = {
    neutral: ["bg-white/10", "text-white", "border-white/15"],
    light: ["bg-white/80", "text-slate-900", "border-slate-200/80"],
    dark: ["bg-slate-900/70", "text-white", "border-slate-700/70"],
  };

  Object.entries(toneClassMap).forEach(([tone, expectedClasses]) => {
    it(`applies tone styles for tone="${tone}"`, () => {
      render(
        <GlassCard tone={tone as any}>
          <span>content</span>
        </GlassCard>
      );

      const wrapper = screen.getByTestId("glass-card");
      expectedClasses.forEach((cls) => {
        expect(wrapper).toHaveClass(cls);
      });
    });
  });

  const paddingClassMap: Record<string, string | null> = {
    none: null,
    sm: "p-3",
    md: "p-4",
    lg: "p-6",
  };

  Object.entries(paddingClassMap).forEach(([padding, expectedClass]) => {
    it(`applies padding styles for padding="${padding}"`, () => {
      render(
        <GlassCard padding={padding as any}>
          <span data-testid="inner" />
        </GlassCard>
      );

      const inner = screen.getByTestId("inner").parentElement as HTMLElement;
      if (expectedClass) {
        expect(inner).toHaveClass(expectedClass);
      } else {
        expect(inner.className).toBe("");
      }
    });
  });

  it("prefers aria-labelledby when both aria props provided", () => {
    render(
      <GlassCard ariaLabel="Example" ariaLabelledBy="title" role="region">
        <span id="title">Title</span>
      </GlassCard>
    );

    const wrapper = screen.getByRole("region");
    expect(wrapper).toHaveAccessibleName("Title");
    expect(wrapper).not.toHaveAttribute("aria-label", "Example");
    expect(wrapper).toHaveAttribute("aria-labelledby", "title");
  });

  it("does not set aria attributes when not provided", () => {
    render(
      <GlassCard>
        <span>Content</span>
      </GlassCard>
    );

    const wrapper = screen.getByTestId("glass-card");
    expect(wrapper).not.toHaveAttribute("aria-label");
    expect(wrapper).not.toHaveAttribute("aria-labelledby");
  });

  it("merges custom class names and forwards misc props", () => {
    render(
      <GlassCard
        id="test-card"
        data-testid="glass-card"
        className="custom-wrapper"
        contentClassName="custom-content"
        padding="none"
      >
        <span data-testid="content">Text</span>
      </GlassCard>
    );

    const wrapper = screen.getByTestId("glass-card");
    expect(wrapper).toHaveClass("custom-wrapper");
    expect(wrapper).toHaveAttribute("id", "test-card");

    const content = screen.getByTestId("content").parentElement as HTMLElement;
    expect(content).toHaveClass("custom-content");
    expect(content.className).toBe("custom-content");
  });

  it('applies default tone styles for invalid tone value', () => {
    render(
      <GlassCard tone="invalid-tone">
        <span>content</span>
      </GlassCard>
    );
    const wrapper = screen.getByTestId("glass-card");
    // Expect default (neutral) classes
    expect(wrapper).toHaveClass("border-white/15");
    expect(wrapper).toHaveClass("bg-white/10");
    expect(wrapper).toHaveClass("text-white");
  });

  it('applies default padding class for invalid padding value', () => {
    render(
      <GlassCard padding={"invalid" as any}>
        <span data-testid="inner" />
      </GlassCard>
    );
    const inner = screen.getByTestId("inner").parentElement as HTMLElement;
    expect(inner).toHaveClass("p-4");
  });
});
