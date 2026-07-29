import { useState } from "react";
import { toArray } from "../utils/format";

export default function MessageBubble({ message, onSpeak, isSpeaking }) {
  const isUser = message.role === "user";
  const recommendations = toArray(message.recommendations);
  const [showWhy, setShowWhy] = useState(false);

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[90%] rounded-2xl px-3.5 py-2.5 ${
          isUser
            ? "rounded-br-md bg-veld-800 text-white"
            : "rounded-bl-md bg-white text-ink shadow-sm ring-1 ring-veld-100"
        }`}
      >
        {!isUser && onSpeak && message.content && (
          <div className="mb-1 flex justify-end">
            <button
              type="button"
              onClick={() => onSpeak(message.content)}
              className="text-[11px] font-semibold text-veld-600"
              aria-label="Speak response"
            >
              {isSpeaking ? "Stop" : "Listen"}
            </button>
          </div>
        )}

        <p className="whitespace-pre-wrap text-sm leading-relaxed">
          {message.content}
        </p>

        {!isUser && recommendations.length > 0 && (
          <ul className="mt-2.5 space-y-1.5 border-t border-veld-100 pt-2.5">
            {recommendations.map((item, index) => (
              <li
                key={`${message.id}-rec-${index}`}
                className="flex gap-2 text-sm text-ink-muted"
              >
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-sun-500" />
                <span>{typeof item === "string" ? item : String(item)}</span>
              </li>
            ))}
          </ul>
        )}

        {!isUser && message.reasoning && (
          <div className="mt-2">
            <button
              type="button"
              onClick={() => setShowWhy((v) => !v)}
              className="text-[11px] font-semibold text-veld-600"
            >
              {showWhy ? "Hide" : "Why?"}
            </button>
            {showWhy && (
              <p className="mt-1.5 whitespace-pre-wrap text-xs leading-relaxed text-ink-muted">
                {message.reasoning}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
