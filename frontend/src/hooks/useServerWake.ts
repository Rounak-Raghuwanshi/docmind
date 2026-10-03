import { useEffect, useState } from "react";
import { API_URL } from "@/lib/api";

/**
 * Free hosting sleeps when idle. Ping /api/health on load; if it's slow, the UI shows a
 * friendly "waking up the server" screen instead of a broken-looking app.
 */
export function useServerWake(): { ready: boolean; waking: boolean } {
  const [ready, setReady] = useState(false);
  const [waking, setWaking] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const slow = setTimeout(() => !cancelled && setWaking(true), 1500);
    (async () => {
      for (let i = 0; i < 60 && !cancelled; i++) {
        try {
          const res = await fetch(`${API_URL}/api/health`, { cache: "no-store" });
          if (res.ok) break;
        } catch {
          /* still asleep */
        }
        await new Promise((r) => setTimeout(r, 3000));
      }
      if (!cancelled) {
        clearTimeout(slow);
        setReady(true);
      }
    })();
    return () => {
      cancelled = true;
      clearTimeout(slow);
    };
  }, []);

  return { ready, waking };
}
