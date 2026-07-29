export function getErrorMessage(error, fallback = "Something went wrong.") {
  if (!error) return fallback;

  if (typeof error === "string") return error;

  if (error.response?.data) {
    const data = error.response.data;
    if (typeof data === "string") return data;
    if (data.detail) {
      if (typeof data.detail === "string") return data.detail;
      if (Array.isArray(data.detail)) {
        return data.detail
          .map((item) => item.msg || item.message || JSON.stringify(item))
          .join("; ");
      }
    }
    if (data.message) return data.message;
    if (data.error) return data.error;
  }

  if (error.message) {
    if (error.code === "ERR_NETWORK") {
      return "Unable to reach the Farmar API. Check that the backend is running.";
    }
    return error.message;
  }

  return fallback;
}

export function formatValue(value, fallback = "—") {
  if (value === null || value === undefined || value === "") return fallback;
  if (typeof value === "object") {
    return Object.entries(value)
      .map(([key, val]) => `${formatLabel(key)}: ${formatValue(val)}`)
      .join(" · ");
  }
  return String(value);
}

export function formatLabel(key) {
  return String(key)
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export function toArray(value) {
  if (!value) return [];
  if (Array.isArray(value)) return value;
  return [value];
}
