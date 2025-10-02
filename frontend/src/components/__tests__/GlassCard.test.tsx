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
    const { container } = render(
      <GlassCard>
        <span data-testid="inner" />
      </GlassCard>
    );

    const wrapper = container.firstElementChild as HTMLElement;
    expect(wrapper).toHaveClass("rounded-2xl");
    expect(wrapper).toHaveClass("bg-white/10");
    expect(wrapper).toHaveClass("text-white");

    const inner = screen.getByTestId("inner").parentElement as HTMLElement;
    expect(inner).toHaveClass("p-4");
  });

  it("respects tone and padding overrides", () => {
    const { container } = render(
      <GlassCard tone="light" padding="lg">
        content
      </GlassCard>
    );

    const wrapper = container.firstElementChild as HTMLElement;
    expect(wrapper).toHaveClass("bg-white/80");
    expect(wrapper).toHaveClass("text-slate-900");

    const inner = wrapper.firstElementChild as HTMLElement;
    expect(inner).toHaveClass("p-6");
  });

  it("allows custom aria attributes and role", () => {
    const { container } = render(
      <GlassCard ariaLabel="Example" ariaLabelledBy="title" role="region">
        <span id="title">Title</span>
      </GlassCard>
    );

    const wrapper = container.firstElementChild as HTMLElement;
    expect(wrapper).toHaveAttribute("aria-label", "Example");
    expect(wrapper).toHaveAttribute("aria-labelledby", "title");
    expect(wrapper).toHaveAttribute("role", "region");
  });

  it("merges custom class names for wrapper and content", () => {
    const { container } = render(
      <GlassCard className="custom-wrapper" contentClassName="custom-content" padding="none">
        <span data-testid="content">Text</span>
      </GlassCard>
    );

    const wrapper = container.firstElementChild as HTMLElement;
    expect(wrapper).toHaveClass("custom-wrapper");

    const content = screen.getByTestId("content").parentElement as HTMLElement;
    expect(content).toHaveClass("custom-content");
    expect(content).not.toHaveClass("p-4");
  });
});
