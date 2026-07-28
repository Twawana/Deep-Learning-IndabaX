import { toArray } from "../utils/format";

export default function MessageBubble({ message }) {
  const isUser = message.role === "user";
  const recommendations = toArray(message.recommendations);

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 sm:max-w-[75%] ${
          isUser
            ? "rounded-br-md bg-veld-800 text-white"
            : "rounded-bl-md border border-veld-200 bg-white text-ink shadow-sm"
        }`}
      >
        {!isUser && (
          <p className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-veld-600">
            Farmar
          </p>
        )}
        <p className="whitespace-pre-wrap text-sm leading-relaxed">
          {message.content}
        </p>

        {recommendations.length > 0 && (
          <div className="mt-3 border-t border-veld-100 pt-3">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-sun-600">
              Recommendations
            </p>
            <ul className="space-y-1.5">
              {recommendations.map((item, index) => (
                <li
                  key={`${message.id}-rec-${index}`}
                  className="flex gap-2 text-sm text-ink-muted"
                >
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-sun-500" />
                  <span>
                    {typeof item === "string" ? item : JSON.stringify(item)}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
