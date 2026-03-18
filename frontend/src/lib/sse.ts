import type { SSEEvent } from "./types";

export function connectSSE(
  url: string,
  onEvent: (event: SSEEvent) => void,
  onClose: () => void,
  onError: (err: Event) => void,
): EventSource {
  const source = new EventSource(url);
  source.onmessage = (e) => {
    try {
      const data: SSEEvent = JSON.parse(e.data);
      onEvent(data);
    } catch {
      console.error("Failed to parse SSE event:", e.data);
    }
  };
  source.onerror = () => {
    // SSE stream naturally closes after graph completes or hits interrupt().
    // This is expected, not an error — call onClose instead of onError.
    source.close();
    onClose();
  };
  return source;
}
