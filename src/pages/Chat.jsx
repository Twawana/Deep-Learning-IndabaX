import ChatBox from "../components/ChatBox";
import ErrorAlert from "../components/ErrorAlert";
import { useChat } from "../hooks/useChat";
import { NAMIBIA_LOCATIONS } from "../utils/constants";

export default function Chat() {
  const {
    messages,
    location,
    setLocation,
    isLoading,
    error,
    clearError,
    send,
    clearChat,
  } = useChat("Windhoek");

  return (
    <div className="flex h-[calc(100vh-7.5rem)] min-h-[32rem] flex-col gap-4">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-sun-600">
            Advisor
          </p>
          <h1 className="mt-1 font-display text-3xl font-bold tracking-tight text-veld-900 sm:text-4xl">
            Farmar AI Chat
          </h1>
          <p className="mt-2 max-w-xl text-sm text-ink-muted">
            Ask practical questions about grazing pressure, stocking rates, and
            when to move your herd.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <label className="sr-only" htmlFor="chat-location">
            Location
          </label>
          <select
            id="chat-location"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            className="rounded-xl border border-veld-200 bg-white px-3 py-2.5 text-sm font-medium text-ink outline-none focus:border-veld-500 focus:ring-2 focus:ring-veld-200"
          >
            {NAMIBIA_LOCATIONS.map((loc) => (
              <option key={loc.name} value={loc.name}>
                {loc.name}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={clearChat}
            className="rounded-xl border border-veld-200 bg-white px-3.5 py-2.5 text-sm font-semibold text-veld-800 transition hover:bg-veld-50"
          >
            Clear chat
          </button>
        </div>
      </div>

      {error && <ErrorAlert message={error} onDismiss={clearError} />}

      <div className="min-h-0 flex-1">
        <ChatBox messages={messages} isLoading={isLoading} onSend={send} />
      </div>
    </div>
  );
}
