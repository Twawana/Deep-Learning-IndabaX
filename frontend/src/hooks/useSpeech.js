import { useCallback, useEffect, useRef, useState } from "react";

function getSpeechRecognition() {
  if (typeof window === "undefined") return null;
  return window.SpeechRecognition || window.webkitSpeechRecognition || null;
}

export function useSpeechToText({ lang = "en-ZA", onResult } = {}) {
  const [isListening, setIsListening] = useState(false);
  const [supported, setSupported] = useState(false);
  const [error, setError] = useState(null);
  const recognitionRef = useRef(null);
  const onResultRef = useRef(onResult);
  onResultRef.current = onResult;

  useEffect(() => {
    const SpeechRecognition = getSpeechRecognition();
    setSupported(Boolean(SpeechRecognition));
    if (!SpeechRecognition) return undefined;

    const recognition = new SpeechRecognition();
    recognition.lang = lang;
    recognition.interimResults = false;
    recognition.continuous = false;

    recognition.onstart = () => setIsListening(true);
    recognition.onend = () => setIsListening(false);
    recognition.onerror = (event) => {
      setIsListening(false);
      if (event.error !== "aborted") {
        setError(event.error || "Speech recognition failed");
      }
    };
    recognition.onresult = (event) => {
      const transcript = Array.from(event.results)
        .map((result) => result[0]?.transcript || "")
        .join(" ")
        .trim();
      if (transcript) onResultRef.current?.(transcript);
    };

    recognitionRef.current = recognition;
    return () => {
      recognition.abort();
      recognitionRef.current = null;
    };
  }, [lang]);

  const start = useCallback(() => {
    setError(null);
    if (!recognitionRef.current) {
      setError("Voice input is not supported in this browser.");
      return;
    }
    try {
      recognitionRef.current.start();
    } catch {
      // Already started
    }
  }, []);

  const stop = useCallback(() => {
    recognitionRef.current?.stop();
  }, []);

  const toggle = useCallback(() => {
    if (isListening) stop();
    else start();
  }, [isListening, start, stop]);

  return { isListening, supported, error, start, stop, toggle, setError };
}

export function useTextToSpeech({ lang = "en-ZA" } = {}) {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [supported] = useState(
    () => typeof window !== "undefined" && "speechSynthesis" in window
  );
  const utteranceRef = useRef(null);

  const stop = useCallback(() => {
    if (typeof window === "undefined") return;
    window.speechSynthesis.cancel();
    setIsSpeaking(false);
  }, []);

  const speak = useCallback(
    (text) => {
      if (!supported || !text?.trim()) return;
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text.trim());
      utterance.lang = lang;
      utterance.rate = 0.95;
      utterance.onstart = () => setIsSpeaking(true);
      utterance.onend = () => setIsSpeaking(false);
      utterance.onerror = () => setIsSpeaking(false);
      utteranceRef.current = utterance;
      window.speechSynthesis.speak(utterance);
    },
    [lang, supported]
  );

  useEffect(() => () => stop(), [stop]);

  return { speak, stop, isSpeaking, supported };
}
