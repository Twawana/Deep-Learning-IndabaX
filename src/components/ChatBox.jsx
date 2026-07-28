import { useEffect, useRef, useState } from "react";
import MessageBubble from "./MessageBubble";
import Loader from "./Loader";
import { CHAT_SUGGESTIONS } from "../utils/constants";

export default function ChatBox({
  messages,
  isLoading,
  onSend,
  disabled = false,
}) {
  const [input, setInput] = useState("");
  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const handleSubmit = (event) => {
    event.preventDefault();
    if (!input.trim() || isLoading || disabled) return;
    onSend(input);
    setInput("");
    inputRef.current?.focus();
  };

  const handleSuggestion = (suggestion) => {
    if (isLoading || disabled) return;
    onSend(suggestion);
  };

  return (
    <div className="flex h-full min-h-[28rem] flex-col overflow-hidden rounded-2xl border border-veld-200/80 bg-white/90 shadow-sm backdrop-blur-sm">
      <div className="flex-1 space-y-4 overflow-y-auto px-4 py-5 sm:px-5">
        {messages.length === 0 && !isLoading ? (
          <div className="flex h-full flex-col items-center justify-center px-2 py-8 text-center">
            <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-veld-100">
              <svg
                className="h-7 w-7 text-veld-700"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.75 20.25a5.971 5.971 0 01-.75-11.25C7.97 3.75 12 7.444 12 12z"
                />
              </svg>
            </div>
            <h3 className="font-display text-xl font-semibold text-veld-900">
              Ask Farmar
            </h3>
            <p className="mt-2 max-w-md text-sm text-ink-muted">
              Get plain-language grazing and livestock advice based on pasture
              data and recent weather for your camp.
            </p>
            <div className="mt-6 flex flex-wrap justify-center gap-2">
              {CHAT_SUGGESTIONS.map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  onClick={() => handleSuggestion(suggestion)}
                  className="rounded-full border border-veld-200 bg-veld-50 px-3 py-1.5 text-left text-xs font-medium text-veld-800 transition hover:border-veld-400 hover:bg-veld-100"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
            {isLoading && (
              <div className="flex justify-start">
                <div className="rounded-2xl rounded-bl-md border border-veld-200 bg-white px-4 py-2 shadow-sm">
                  <Loader label="Farmar is thinking…" />
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </>
        )}
      </div>

      <form
        onSubmit={handleSubmit}
        className="border-t border-veld-100 bg-veld-50/60 p-3 sm:p-4"
      >
        <div className="flex items-end gap-2">
          <label className="sr-only" htmlFor="chat-input">
            Message
          </label>
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
            placeholder="Ask about grazing, stocking rates, or bush encroachment…"
            disabled={isLoading || disabled}
            className="max-h-32 min-h-[2.75rem] flex-1 resize-none rounded-xl border border-veld-200 bg-white px-3.5 py-2.5 text-sm text-ink outline-none transition placeholder:text-ink-muted/70 focus:border-veld-500 focus:ring-2 focus:ring-veld-200 disabled:opacity-60"
          />
          <button
            type="submit"
            disabled={!input.trim() || isLoading || disabled}
            className="inline-flex h-11 shrink-0 items-center justify-center rounded-xl bg-veld-800 px-4 text-sm font-semibold text-white transition hover:bg-veld-900 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Send
          </button>
        </div>
      </form>
    </div>
  );
}
