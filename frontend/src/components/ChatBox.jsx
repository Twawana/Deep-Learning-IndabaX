import { useEffect, useRef, useState } from "react";
import MessageBubble from "./MessageBubble";
import Loader from "./Loader";
import { CHAT_SUGGESTIONS } from "../utils/constants";
import { useSpeechToText, useTextToSpeech } from "../hooks/useSpeech";
import { toArray } from "../utils/format";

function speakableText(message) {
  const parts = [message.content];
  const recs = toArray(message.recommendations);
  if (recs.length) {
    parts.push("Recommendations:");
    recs.forEach((item, i) => {
      parts.push(`${i + 1}. ${typeof item === "string" ? item : String(item)}`);
    });
  }
  return parts.filter(Boolean).join("\n");
}

export default function ChatBox({
  messages,
  isLoading,
  onSend,
  disabled = false,
  suggestions,
  emptyPrompt = "Ask about your pasture or herd",
}) {
  const [input, setInput] = useState("");
  const [autoRead, setAutoRead] = useState(false);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);
  const lastSpokenIdRef = useRef(null);
  const chips = suggestions?.length ? suggestions : CHAT_SUGGESTIONS.slice(0, 3);

  const {
    speak,
    stop: stopSpeaking,
    isSpeaking,
    speakingId,
    supported: ttsSupported,
  } = useTextToSpeech();

  const {
    isListening,
    supported: sttSupported,
    error: sttError,
    toggle: toggleListen,
    stop: stopListening,
    setError: setSttError,
  } = useSpeechToText({
    onResult: (transcript) => {
      setInput((prev) => (prev ? `${prev} ${transcript}` : transcript));
      inputRef.current?.focus();
    },
  });

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  // Auto-read newest AI reply when enabled
  useEffect(() => {
    if (!autoRead || !ttsSupported || isLoading) return;
    const last = messages[messages.length - 1];
    if (!last || last.role !== "assistant") return;
    if (lastSpokenIdRef.current === last.id) return;
    lastSpokenIdRef.current = last.id;
    speak(speakableText(last), { id: last.id });
  }, [autoRead, ttsSupported, isLoading, messages, speak]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!input.trim() || isLoading || disabled) return;
    stopListening();
    stopSpeaking();
    const text = input;
    setInput("");
    await onSend(text);
    inputRef.current?.focus();
  };

  const handleSpeak = (message) => {
    if (isSpeaking && speakingId === message.id) {
      stopSpeaking();
      return;
    }
    stopListening();
    speak(speakableText(message), { id: message.id });
  };

  const handleMic = () => {
    if (isSpeaking) stopSpeaking();
    toggleListen();
  };

  return (
    <div className="flex h-full min-h-0 flex-col bg-mist">
      <div className="flex items-center justify-between gap-2 border-b border-veld-100 bg-white px-3 py-1.5">
        <p className="text-[11px] text-ink-muted">
          {sttSupported
            ? "Tap the mic to speak your question"
            : "Voice input needs Chrome or Edge"}
        </p>
        {ttsSupported && (
          <label className="flex items-center gap-1.5 text-[11px] font-medium text-veld-800">
            <input
              type="checkbox"
              checked={autoRead}
              onChange={(e) => {
                const on = e.target.checked;
                setAutoRead(on);
                if (!on) stopSpeaking();
              }}
              className="rounded border-veld-300"
            />
            Read replies aloud
          </label>
        )}
      </div>

      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto overscroll-contain px-3 py-3">
        {messages.length === 0 && !isLoading ? (
          <div className="flex h-full flex-col justify-center gap-2 py-6">
            <p className="mb-1 px-1 text-center text-sm text-ink-muted">
              {emptyPrompt}
            </p>
            {chips.map((suggestion) => (
              <button
                key={suggestion}
                type="button"
                onClick={() => onSend(suggestion)}
                disabled={isLoading || disabled}
                className="rounded-2xl bg-white px-4 py-3.5 text-left text-sm font-medium text-veld-900 shadow-sm ring-1 ring-veld-100 active:bg-veld-50"
              >
                {suggestion}
              </button>
            ))}
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <MessageBubble
                key={message.id}
                message={message}
                onSpeak={ttsSupported ? () => handleSpeak(message) : undefined}
                isSpeaking={speakingId === message.id}
              />
            ))}
            {isLoading && (
              <div className="flex justify-start">
                <div className="rounded-2xl bg-white px-3 py-1 shadow-sm ring-1 ring-veld-100">
                  <Loader label="Thinking…" compact />
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </>
        )}
      </div>

      {sttError && (
        <div className="border-t border-amber-100 bg-amber-50 px-3 py-2 text-xs text-amber-900">
          <div className="flex items-start justify-between gap-2">
            <span>{sttError}</span>
            <button
              type="button"
              onClick={() => setSttError(null)}
              className="shrink-0 font-semibold"
            >
              Dismiss
            </button>
          </div>
        </div>
      )}

      <form
        onSubmit={handleSubmit}
        className="border-t border-veld-100 bg-white px-3 py-2.5"
      >
        <div className="flex items-end gap-2">
          <button
            type="button"
            onClick={handleMic}
            disabled={isLoading || disabled || !sttSupported}
            aria-label={isListening ? "Stop listening" : "Speak question"}
            title={
              sttSupported
                ? isListening
                  ? "Stop listening"
                  : "Speak your question"
                : "Voice input not supported in this browser"
            }
            className={`inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-full ${
              isListening
                ? "bg-danger text-white ring-2 ring-danger/30"
                : "bg-mist text-veld-800 active:bg-veld-100"
            } disabled:opacity-40`}
          >
            <svg className="h-5 w-5" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
              <path d="M12 14a3 3 0 003-3V6a3 3 0 10-6 0v5a3 3 0 003 3zm5-3a5 5 0 01-10 0H5a7 7 0 0014 0h-2zM11 18.93V22h2v-3.07A8.001 8.001 0 0020 11h-2a6 6 0 11-12 0H4a8.001 8.001 0 007 7.93z" />
            </svg>
          </button>

          <textarea
            id="chat-input"
            ref={inputRef}
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e);
              }
            }}
            placeholder={isListening ? "Listening… speak now" : "Type or speak your question…"}
            disabled={isLoading || disabled}
            className="max-h-28 min-h-[2.75rem] flex-1 resize-none rounded-2xl border-0 bg-mist px-3.5 py-2.5 text-sm text-ink outline-none ring-1 ring-veld-200 focus:ring-2 focus:ring-veld-400 disabled:opacity-60"
          />
          <button
            type="submit"
            disabled={!input.trim() || isLoading || disabled}
            aria-label="Send"
            className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-veld-800 text-white active:bg-veld-900 disabled:opacity-40"
          >
            <svg className="h-5 w-5" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
              <path d="M3.4 20.4l17.45-7.48a1 1 0 000-1.84L3.4 3.6a.993.993 0 00-1.39.91L2 9.12c0 .5.37.93.87.99L17 12 2.87 13.88c-.5.07-.87.5-.87 1l.01 4.61c0 .71.73 1.2 1.39.91z" />
            </svg>
          </button>
        </div>
      </form>
    </div>
  );
}
