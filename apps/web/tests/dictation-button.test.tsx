import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DictationButton } from "@/components/dictation-button";

class MockRecognition {
  static instance: MockRecognition | null = null;
  continuous = false;
  interimResults = false;
  onend: (() => void) | null = null;
  onerror: ((event: { error: string }) => void) | null = null;
  onresult: ((event: { resultIndex: number; results: unknown }) => void) | null = null;
  abort = vi.fn();
  start = vi.fn();
  stop = vi.fn();

  constructor() {
    MockRecognition.instance = this;
  }
}

afterEach(() => {
  cleanup();
  MockRecognition.instance = null;
  delete (window as Window & { SpeechRecognition?: unknown }).SpeechRecognition;
});

describe("DictationButton", () => {
  it("appends the recognized transcript after the user starts dictation", async () => {
    Object.defineProperty(window, "SpeechRecognition", {
      configurable: true,
      value: MockRecognition,
    });
    const user = userEvent.setup();
    const onTranscript = vi.fn();
    render(<DictationButton label="event details" onTranscript={onTranscript} />);

    await user.click(await screen.findByRole("button", { name: "Dictate event details" }));
    expect(MockRecognition.instance?.start).toHaveBeenCalledOnce();

    MockRecognition.instance?.onresult?.({
      resultIndex: 0,
      results: [[{ transcript: "Booked a flight to Tokyo" }]],
    });

    expect(onTranscript).toHaveBeenCalledWith("Booked a flight to Tokyo");
  });

  it("remains unavailable when the browser has no speech recognition support", () => {
    render(<DictationButton label="event details" onTranscript={vi.fn()} />);

    expect(screen.queryByRole("button", { name: /dictate event details/i })).not.toBeInTheDocument();
  });
});
