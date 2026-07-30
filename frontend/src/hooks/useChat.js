import { useCallback, useState } from "react";
import { sendMessage } from "../services/api";
import { datasetLocation } from "../utils/constants";
import { getErrorMessage } from "../utils/format";
import { useFarmContext } from "../context/FarmContext";
import { useAuth } from "../context/AuthContext";

function toOptionalInt(value) {
  if (value === "" || value === null || value === undefined) return undefined;
  const n = Number(value);
  return Number.isFinite(n) ? n : undefined;
}

export function useChat() {
  const farm = useFarmContext();
  const {
    userTier,
    isLoggedIn,
    isPremium,
    isAdmin,
    canAskAsGuest,
    guestAsksRemaining,
    trackAiUsage,
    appSettings,
  } = useAuth();
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastTools, setLastTools] = useState([]);

  const clearError = useCallback(() => setError(null), []);

  const send = useCallback(
    async (text) => {
      const trimmed = text.trim();
      if (!trimmed || isLoading) return null;

      if (appSettings?.maintenanceMode && !isAdmin) {
        setError(
          "Ask is temporarily limited while maintenance mode is on. Try again later."
        );
        return null;
      }

      if (!isLoggedIn && !canAskAsGuest) {
        setError(
          "Guest Ask limit reached. Log in on Profile for unlimited free answers, or upgrade for Premium AI."
        );
        return null;
      }

      const location = datasetLocation(farm);
      if (!location) {
        setError("Set a supported town or research site in your profile first.");
        return null;
      }

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

      // Guests and free accounts get free-tier answers; premium only when logged in + upgraded.
      const effectiveTier = isPremium ? "premium" : "free";

      try {
        const data = await sendMessage({
          message: trimmed,
          nearest_town: location,
          location: location,
          region: farm.region,
          village: farm.village || undefined,
          farmer_name: farm.farmerName || undefined,
          farm_name: farm.farmName || undefined,
          phone: farm.phone || undefined,
          herd_size: toOptionalInt(farm.herdSize),
          livestock_type: farm.livestockType || undefined,
          camp_name: farm.campName || undefined,
          number_of_camps: toOptionalInt(farm.numberOfCamps),
          farm_size_ha: toOptionalInt(farm.farmSizeHa),
          land_tenure: farm.landTenure,
          water_source: farm.waterSource || undefined,
          farm_notes:
            [farm.farmNotes, farm.customLocation].filter(Boolean).join(" | ") ||
            undefined,
          lat: Number(farm.lat),
          lon: Number(farm.lon),
          user_tier: effectiveTier,
          is_guest: !isLoggedIn,
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
          decision: data.decision || null,
          limitations: data.limitations || "",
          user_tier: data.user_tier || effectiveTier,
          timestamp: new Date().toISOString(),
        };

        setLastTools(aiMessage.tools_used);
        setMessages((prev) => [...prev, aiMessage]);
        try {
          await trackAiUsage();
        } catch {
          // Usage tracking is best-effort and should not block chat.
        }
        return aiMessage;
      } catch (err) {
        setError(getErrorMessage(err, "Failed to send message."));
        return null;
      } finally {
        setIsLoading(false);
      }
    },
    [
      farm,
      isLoading,
      messages,
      userTier,
      isLoggedIn,
      isPremium,
      isAdmin,
      canAskAsGuest,
      trackAiUsage,
      appSettings?.maintenanceMode,
    ]
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
    guestAsksRemaining,
    isLoggedIn,
  };
}
