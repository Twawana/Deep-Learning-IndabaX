import { useCallback, useEffect, useRef, useState } from "react";

const LANG_FALLBACKS = ["en-ZA", "en-GB", "en-US", "en"];

function getSpeechRecognition() {
  if (typeof window === "undefined") return null;
  return window.SpeechRecognition || window.webkitSpeechRecognition || null;
}

function friendlySttError(code) {
  switch (code) {
    case "not-allowed":
    case "service-not-allowed":
      return "Microphone permission denied. Allow mic access in the browser, then try again.";
    case "no-speech":
      return "No speech heard. Hold the mic and speak clearly.";
    case "audio-capture":
      return "No microphone found. Plug in a mic or check device settings.";
    case "network":
      return "Speech recognition needs network access (Chrome uses an online service).";
    case "aborted":
      return null;
    default:
      return code ? `Speech recognition failed (${code}).` : "Speech recognition failed.";
  }
}

function pickVoice(lang) {
  if (typeof window === "undefined" || !window.speechSynthesis) return null;
  const voices = window.speechSynthesis.getVoices();
  if (!voices.length) return null;

  const preferred = [lang, ...LANG_FALLBACKS];
  for (const code of preferred) {
    const exact = voices.find((v) => v.lang === code);
    if (exact) return exact;
    const prefix = code.split("-")[0];
    const fuzzy = voices.find((v) => v.lang?.toLowerCase().startsWith(prefix.toLowerCase()));
    if (fuzzy) return fuzzy;
  }
  return voices.find((v) => v.default) || voices[0];
}

/** Split long advisor text so Chrome TTS does not cut off mid-reply. */
function chunkForSpeech(text, maxLen = 220) {
  const cleaned = text.replace(/\s+/g, " ").trim();
  if (cleaned.length <= maxLen) return [cleaned];

  const sentences = cleaned.match(/[^.!?]+[.!?]+|[^.!?]+$/g) || [cleaned];
  const chunks = [];
  let current = "";
  for (const sentence of sentences) {
    const piece = sentence.trim();
    if (!piece) continue;
    if ((current + " " + piece).trim().length <= maxLen) {
      current = (current + " " + piece).trim();
    } else {
      if (current) chunks.push(current);
      if (piece.length <= maxLen) {
        current = piece;
      } else {
        // Hard-split very long sentences
        for (let i = 0; i < piece.length; i += maxLen) {
          chunks.push(piece.slice(i, i + maxLen));
        }
        current = "";
      }
    }
  }
  if (current) chunks.push(current);
  return chunks.length ? chunks : [cleaned];
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
    recognition.interimResults = true;
    recognition.continuous = false;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
      setIsListening(true);
      setError(null);
    };
    recognition.onend = () => setIsListening(false);
    recognition.onerror = (event) => {
      setIsListening(false);
      const message = friendlySttError(event.error);
      if (message) setError(message);
    };
    recognition.onresult = (event) => {
      // Prefer final transcript; fall back to latest interim if session ends mid-stream
      let finalText = "";
      let interimText = "";
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const piece = event.results[i][0]?.transcript || "";
        if (event.results[i].isFinal) finalText += `${piece} `;
        else interimText += `${piece} `;
      }
      const transcript = (finalText || interimText).trim();
      if (finalText.trim()) {
        onResultRef.current?.(finalText.trim());
      } else if (
        transcript &&
        event.results.length &&
        event.results[event.results.length - 1].isFinal
      ) {
        onResultRef.current?.(transcript);
      }
    };

    recognitionRef.current = recognition;
    return () => {
      try {
        recognition.onresult = null;
        recognition.onerror = null;
        recognition.onend = null;
        recognition.abort();
      } catch {
        // ignore cleanup errors
      }
      recognitionRef.current = null;
    };
  }, [lang]);

  const start = useCallback(async () => {
    setError(null);
    if (!recognitionRef.current) {
      setError(
        "Voice input is not supported in this browser. Try Chrome or Edge on desktop, or Chrome on Android."
      );
      return;
    }

    // Prompt for mic early so "not-allowed" is clearer
    if (navigator.mediaDevices?.getUserMedia) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        stream.getTracks().forEach((t) => t.stop());
      } catch {
        setError(
          "Microphone permission denied. Allow mic access in the browser, then try again."
        );
        return;
      }
    }

    try {
      recognitionRef.current.lang = lang;
      recognitionRef.current.start();
    } catch {
      // Already started — restart cleanly
      try {
        recognitionRef.current.stop();
        setTimeout(() => {
          try {
            recognitionRef.current?.start();
          } catch {
            setError("Could not start the microphone. Try again.");
          }
        }, 200);
      } catch {
        setError("Could not start the microphone. Try again.");
      }
    }
  }, [lang]);

  const stop = useCallback(() => {
    try {
      recognitionRef.current?.stop();
    } catch {
      // ignore
    }
  }, []);

  const toggle = useCallback(() => {
    if (isListening) stop();
    else start();
  }, [isListening, start, stop]);

  return { isListening, supported, error, start, stop, toggle, setError };
}

export function useTextToSpeech({ lang = "en-ZA" } = {}) {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [speakingId, setSpeakingId] = useState(null);
  const [supported] = useState(
    () => typeof window !== "undefined" && "speechSynthesis" in window
  );
  const utteranceRef = useRef(null);
  const resumeTimerRef = useRef(null);
  const generationRef = useRef(0);

  const clearResumeTimer = useCallback(() => {
    if (resumeTimerRef.current) {
      clearInterval(resumeTimerRef.current);
      resumeTimerRef.current = null;
    }
  }, []);

  const stop = useCallback(() => {
    if (typeof window === "undefined") return;
    generationRef.current += 1;
    clearResumeTimer();
    window.speechSynthesis.cancel();
    setIsSpeaking(false);
    setSpeakingId(null);
    utteranceRef.current = null;
  }, [clearResumeTimer]);

  // Chrome loads voices asynchronously
  useEffect(() => {
    if (!supported) return undefined;
    const warm = () => window.speechSynthesis.getVoices();
    warm();
    window.speechSynthesis.addEventListener("voiceschanged", warm);
    return () => window.speechSynthesis.removeEventListener("voiceschanged", warm);
  }, [supported]);

  const speak = useCallback(
    (text, { id = null } = {}) => {
      if (!supported || !text?.trim()) return;

      stop();
      const generation = generationRef.current;

      const chunks = chunkForSpeech(text.trim());
      const voice = pickVoice(lang);
      let index = 0;

      const speakNext = () => {
        if (generation !== generationRef.current) return;
        if (index >= chunks.length) {
          clearResumeTimer();
          setIsSpeaking(false);
          setSpeakingId(null);
          return;
        }
        const utterance = new SpeechSynthesisUtterance(chunks[index]);
        utterance.lang = voice?.lang || lang;
        utterance.rate = 0.95;
        utterance.pitch = 1;
        if (voice) utterance.voice = voice;

        utterance.onstart = () => {
          if (generation !== generationRef.current) return;
          setIsSpeaking(true);
          setSpeakingId(id);
        };
        utterance.onend = () => {
          if (generation !== generationRef.current) return;
          index += 1;
          speakNext();
        };
        utterance.onerror = () => {
          if (generation !== generationRef.current) return;
          clearResumeTimer();
          setIsSpeaking(false);
          setSpeakingId(null);
        };

        utteranceRef.current = utterance;
        window.speechSynthesis.speak(utterance);
      };

      speakNext();

      clearResumeTimer();
      resumeTimerRef.current = setInterval(() => {
        if (generation !== generationRef.current) {
          clearResumeTimer();
          return;
        }
        if (!window.speechSynthesis.speaking && !window.speechSynthesis.pending) {
          clearResumeTimer();
          return;
        }
        if (window.speechSynthesis.paused) {
          window.speechSynthesis.resume();
        }
      }, 4000);
    },
    [clearResumeTimer, lang, stop, supported]
  );

  useEffect(() => () => stop(), [stop]);

  return { speak, stop, isSpeaking, speakingId, supported };
}
