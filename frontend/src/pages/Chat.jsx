import ChatBox from "../components/ChatBox";
import ErrorAlert from "../components/ErrorAlert";
import FarmContextBar from "../components/FarmContextBar";
import GuestBanner from "../components/GuestBanner";
import { useChat } from "../hooks/useChat";
import { useAuth } from "../context/AuthContext";

export default function Chat() {
  const { messages, isLoading, error, clearError, send, clearChat, guestAsksRemaining } =
    useChat();
  const { isLoggedIn, isPremium } = useAuth();

  return (
    <div className="flex h-full min-h-0 flex-col">
      <FarmContextBar />

      {!isLoggedIn ? (
        <div className="border-b border-veld-100 px-3 py-2">
          <GuestBanner
            title="Guest Ask · In Vision"
            detail={`Basic answers available (${guestAsksRemaining} left). Log in for unlimited free Ask, or upgrade for Premium In Vision.`}
          />
        </div>
      ) : !isPremium ? (
        <div className="border-b border-veld-100 bg-white px-3 py-2 text-xs text-ink-muted">
          Free plan: short In Vision answers. Upgrade on Profile for detailed grazing advice.
        </div>
      ) : (
        <div className="border-b border-veld-100 bg-white px-3 py-2 text-xs text-ink-muted">
          Talking with <span className="font-semibold text-veld-800">In Vision</span> — your rangeland assistant.
        </div>
      )}

      {messages.length > 0 && (
        <div className="flex justify-end border-b border-veld-100 bg-white px-3 py-1.5">
          <button
            type="button"
            onClick={clearChat}
            className="text-xs font-semibold text-veld-700"
          >
            Clear chat
          </button>
        </div>
      )}

      {error && (
        <div className="px-3 pt-2">
          <ErrorAlert message={error} onDismiss={clearError} />
        </div>
      )}

      <div className="min-h-0 flex-1">
        <ChatBox
          messages={messages}
          isLoading={isLoading}
          onSend={send}
          emptyPrompt="Ask In Vision a grazing decision — stay, move, stocking, rainfall…"
        />
      </div>
    </div>
  );
}
