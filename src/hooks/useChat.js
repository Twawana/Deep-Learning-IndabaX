import { useCallback, useState } from "react";
import { sendMessage } from "../services/api";
import { getErrorMessage } from "../utils/format";
import { useFarmContext } from "../context/FarmContext";

export function useChat() {
  const farm = useFarmContext();
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastTools, setLastTools] = useState([]);

  const clearError = useCallback(() => setError(null), []);

  const send = useCallback(
    async (text) => {
      const trimmed = text.trim();
      if (!trimmed || isLoading) return null;

      const userMessage = {
        id: `user-${Date.now()}`,
        role: "user",
        content: trimmed,
        timestamp: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, userMessage]);
      setIsLoading(true);
      setError(null);

      const history = [...messages, userMessage].map((m) => ({
        role: m.role,
        content: m.content,
      }));

      try {
        const data = await sendMessage({
          message: trimmed,
          farmer_name: farm.farmerName || undefined,
          location: farm.location,
          region: farm.region,
          herd_size: Number(farm.herdSize) || undefined,
          camp_name: farm.campName || undefined,
          land_tenure: farm.landTenure,
          lat: farm.lat,
          lon: farm.lon,
          history,
        });

        const aiMessage = {
          id: `ai-${Date.now()}`,
          role: "assistant",
          content: data.response || data.message || "No response received.",
          reasoning: data.reasoning || "",
          recommendations: data.recommendations || [],
          tools_used: data.tools_used || [],
          sources: data.sources || null,
          limitations: data.limitations || "",
          timestamp: new Date().toISOString(),
        };

        setLastTools(aiMessage.tools_used);
        setMessages((prev) => [...prev, aiMessage]);
        return aiMessage;
      } catch (err) {
        setError(getErrorMessage(err, "Failed to send message."));
        return null;
      } finally {
        setIsLoading(false);
      }
    },
    [farm, isLoading, messages]
  );

  const clearChat = useCallback(() => {
    setMessages([]);
    setLastTools([]);
    setError(null);
  }, []);

  return {
    messages,
    isLoading,
    error,
    clearError,
    send,
    clearChat,
    lastTools,
  };
}
