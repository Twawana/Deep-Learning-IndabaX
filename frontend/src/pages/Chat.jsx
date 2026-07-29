import ChatBox from "../components/ChatBox";
import ErrorAlert from "../components/ErrorAlert";
import FarmContextBar from "../components/FarmContextBar";
import { useChat } from "../hooks/useChat";

export default function Chat() {
  const { messages, isLoading, error, clearError, send, clearChat } = useChat();

  return (
    <div className="flex h-full min-h-0 flex-col">
      <FarmContextBar />

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
        <ChatBox messages={messages} isLoading={isLoading} onSend={send} />
      </div>
    </div>
  );
}
