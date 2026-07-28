import { useCallback, useState } from "react";
import { sendMessage } from "../services/api";
import { getErrorMessage } from "../utils/format";

export function useChat(defaultLocation = "Windhoek") {
  const [messages, setMessages] = useState([]);
  const [location, setLocation] = useState(defaultLocation);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const clearError = useCallback(() => setError(null), []);

  const send = useCallback(
    async (text) => {
      const trimmed = text.trim();
      if (!trimmed || isLoading) return;

      const userMessage = {
        id: `user-${Date.now()}`,
        role: "user",
        content: trimmed,
        timestamp: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, userMessage]);
      setIsLoading(true);
      setError(null);

      try {
        const data = await sendMessage(trimmed, location);
        const aiMessage = {
          id: `ai-${Date.now()}`,
          role: "assistant",
          content: data.response || data.message || "No response received.",
          recommendations: data.recommendations || [],
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, aiMessage]);
      } catch (err) {
        setError(getErrorMessage(err, "Failed to send message."));
      } finally {
        setIsLoading(false);
      }
    },
    [isLoading, location]
  );

  const clearChat = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return {
    messages,
    location,
    setLocation,
    isLoading,
    error,
    clearError,
    send,
    clearChat,
  };
}
