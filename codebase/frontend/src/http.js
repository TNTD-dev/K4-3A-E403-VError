export function formatApiError(data) {
  if (typeof data?.message === "string" && data.message) return data.message;
  if (typeof data?.error === "string" && data.error) return data.error;
  const detail = data?.detail;
  if (typeof detail === "string" && detail) return detail;
  if (Array.isArray(detail) && detail.length) {
    return detail
      .map(item => (typeof item === "string" ? item : item?.msg || JSON.stringify(item)))
      .filter(Boolean)
      .join("; ");
  }
  if (detail && typeof detail === "object") return JSON.stringify(detail);
  return "Có lỗi xảy ra";
}

/** Merge fetch options so Content-Type is never dropped by caller headers. */
export function buildFetchInit(options = {}) {
  const { headers: extraHeaders, ...rest } = options;
  return {
    ...rest,
    headers: {
      "Content-Type": "application/json",
      ...(extraHeaders || {}),
    },
  };
}
