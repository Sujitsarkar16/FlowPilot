"use client";

import { useEffect, useRef, useState } from "react";
import { Mic } from "lucide-react";

import { Button } from "@/components/ui/button";

type RecognitionEvent = {
  resultIndex: number;
  results: { length: number; [index: number]: { [index: number]: { transcript: string } } };
};

type Recognition = {
  continuous: boolean;
  interimResults: boolean;
  onend: (() => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onresult: ((event: RecognitionEvent) => void) | null;
  abort: () => void;
  start: () => void;
  stop: () => void;
};

type RecognitionConstructor = new () => Recognition;
type SpeechRecognitionWindow = Window & {
  SpeechRecognition?: RecognitionConstructor;
  webkitSpeechRecognition?: RecognitionConstructor;
};

function recognitionConstructor(): RecognitionConstructor | undefined {
  if (typeof window === "undefined") return undefined;
  const speechWindow = window as SpeechRecognitionWindow;
  return speechWindow.SpeechRecognition ?? speechWindow.webkitSpeechRecognition;
}

function dictationError(error: string) {
  if (error === "not-allowed" || error === "service-not-allowed") {
    return new Error("Microphone access was denied. Allow it in your browser settings to dictate.");
  }
  return new Error("Dictation stopped unexpectedly. Please try again.");
}

export function DictationButton({
  disabled = false,
  label,
  onError,
  onTranscript,
}: {
  disabled?: boolean;
  label: string;
  onError?: (error: Error) => void;
  onTranscript: (transcript: string) => void;
}) {
  const recognitionRef = useRef<Recognition | null>(null);
  const [supported, setSupported] = useState(false);
  const [listening, setListening] = useState(false);

  useEffect(() => {
    setSupported(Boolean(recognitionConstructor()));
    return () => recognitionRef.current?.abort();
  }, []);

  const toggle = () => {
    if (listening) {
      recognitionRef.current?.stop();
      return;
    }

    const Constructor = recognitionConstructor();
    if (!Constructor) return;
    const recognition = new Constructor();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.onresult = (event) => {
      const transcript = Array.from(
        { length: event.results.length - event.resultIndex },
        (_, index) => event.results[event.resultIndex + index][0].transcript,
      ).join("").trim();
      if (transcript) onTranscript(transcript);
    };
    recognition.onerror = (event) => onError?.(dictationError(event.error));
    recognition.onend = () => {
      recognitionRef.current = null;
      setListening(false);
    };
    recognitionRef.current = recognition;
    try {
      recognition.start();
      setListening(true);
    } catch {
      recognitionRef.current = null;
      setListening(false);
      onError?.(new Error("Dictation could not start. Please try again."));
    }
  };

  if (!supported) return null;

  return (
    <Button
      aria-label={`${listening ? "Stop dictating" : "Dictate"} ${label}`}
      aria-pressed={listening}
      disabled={disabled}
      onClick={toggle}
      size="sm"
      type="button"
      variant="outline"
    >
      <Mic aria-hidden="true" className="mr-1.5 h-3.5 w-3.5" />
      {listening ? "Stop dictation" : "Dictate"}
    </Button>
  );
}
