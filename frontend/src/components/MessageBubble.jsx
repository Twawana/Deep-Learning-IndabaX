import { useState } from "react";
import { toArray } from "../utils/format";
import { priorityStyle } from "./decision/priorityStyles";
import StatusDot from "./decision/StatusDot";

export default function MessageBubble({ message, onSpeak, isSpeaking }) {
  const isUser = message.role === "user";
  const recommendations = toArray(message.recommendations);
  const toolsUsed = toArray(message.tools_used);
  const limitations =
    typeof message.limitations === "string"
      ? message.limitations
          .split(";")
          .map((s) => s.trim())
          .filter(Boolean)
      : toArray(message.limitations);
  const decision = message.decision;
  const showDecisionUi = Boolean(decision);
  const [showWhy, setShowWhy] = useState(false);
  const [showEvidence, setShowEvidence] = useState(false);

  const style = priorityStyle(decision?.action_priority || "monitor");

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[90%] rounded-2xl px-3.5 py-2.5 lg:max-w-[42rem] ${
          isUser
            ? "rounded-br-md bg-veld-800 text-white"
            : "rounded-bl-md bg-white text-ink shadow-sm ring-1 ring-veld-100"
        }`}
      >
        {!isUser && onSpeak && message.content && (
          <div className="mb-1 flex justify-end">
            <button
              type="button"
              onClick={onSpeak}
              className={`text-[11px] font-semibold ${
                isSpeaking ? "text-danger" : "text-veld-600"
              }`}
              aria-label={isSpeaking ? "Stop speaking" : "Listen to response"}
            >
              {isSpeaking ? "Stop" : "Listen"}
            </button>
          </div>
        )}

        {!isUser && showDecisionUi && decision?.headline && (
          <p className={`mb-2 inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-semibold ring-1 ${style.badge}`}>
            <StatusDot style={style} />
            {decision.headline}
          </p>
        )}

        {!isUser && message.assistant?.name && (
          <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wide text-veld-600">
            {message.assistant.name}
            {message.assistant.powered_by === "gemini"
              ? message.assistant.mode === "agentic_tool_calling"
                ? " · agent"
                : " · AI"
              : ""}
          </p>
        )}

        {!isUser && showDecisionUi && Array.isArray(decision?.what_changed) && decision.what_changed.length > 0 && (
          <ul className="mb-2 space-y-1 rounded-xl bg-mist px-2.5 py-2">
            {decision.what_changed.slice(0, 3).map((item) => (
              <li key={item} className="text-[11px] leading-relaxed text-veld-800">
                • {item}
              </li>
            ))}
          </ul>
        )}

        <p className="whitespace-pre-wrap text-sm leading-relaxed">
          {message.content}
        </p>

        {!isUser && showDecisionUi && recommendations.length > 0 && (
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

        {!isUser && showDecisionUi && decision?.explainer?.checks?.length > 0 && (
          <div className="mt-2.5 border-t border-veld-100 pt-2">
            <p className="text-[11px] font-semibold text-veld-800">
              Why this recommendation?
            </p>
            <ul className="mt-1.5 space-y-1">
              {decision.explainer.checks.map((check) => (
                <li key={check.id} className="text-[11px] text-ink-muted">
                  {check.done ? "✓" : "○"} {check.label}
                </li>
              ))}
            </ul>
            {(decision.explainer.why || []).length > 0 && (
              <ul className="mt-2 space-y-1">
                {decision.explainer.why.slice(0, 3).map((item) => (
                  <li key={item} className="text-[11px] leading-relaxed text-ink-muted">
                    • {item}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

        {!isUser && showDecisionUi && toolsUsed.length > 0 && message.user_tier !== "free" && (
          <p className="mt-2 text-[11px] text-ink-muted">
            Tools:{" "}
            {toolsUsed
              .map((t) => (typeof t === "string" ? t : t?.name || String(t)))
              .join(", ")}
          </p>
        )}

        {!isUser && showDecisionUi && limitations.length > 0 && message.user_tier !== "free" && (
          <ul className="mt-2 space-y-1 border-t border-veld-100 pt-2">
            {limitations.map((item, index) => (
              <li
                key={`${message.id}-lim-${index}`}
                className="text-[11px] leading-relaxed text-ink-muted"
              >
                {typeof item === "string" ? item : String(item)}
              </li>
            ))}
          </ul>
        )}

        {!isUser &&
          showDecisionUi &&
          (message.reasoning || message.sources) &&
          message.user_tier !== "free" && (
          <div className="mt-2 flex flex-wrap gap-3">
            {message.reasoning && (
              <button
                type="button"
                onClick={() => setShowWhy((v) => !v)}
                className="text-[11px] font-semibold text-veld-600"
              >
                {showWhy ? "Hide reasoning" : "View reasoning"}
              </button>
            )}
            {message.sources && (
              <button
                type="button"
                onClick={() => setShowEvidence((v) => !v)}
                className="text-[11px] font-semibold text-veld-600"
              >
                {showEvidence ? "Hide evidence" : "View evidence"}
              </button>
            )}
          </div>
        )}

        {!isUser && showWhy && message.reasoning && (
          <p className="mt-1.5 whitespace-pre-wrap text-xs leading-relaxed text-ink-muted">
            {message.reasoning}
          </p>
        )}

        {!isUser && showEvidence && message.sources && (
          <pre className="mt-1.5 max-h-40 overflow-auto rounded-lg bg-mist p-2 text-[10px] text-ink-muted">
            {JSON.stringify(message.sources, null, 2)}
          </pre>
        )}
      </div>
    </div>
  );
}
