/**
 * The one place the app shows toast notifications. Components call notify.* instead of a
 * toast library directly, so every message looks and behaves the same, and swapping the
 * library later touches a single file.
 */
import { toast } from "sonner";
import { ApiError } from "./api";

function describe(err: unknown, fallback: string): { message: string; requestId?: string } {
  if (err instanceof ApiError) return { message: err.message, requestId: err.requestId };
  if (err instanceof Error && err.message) return { message: err.message };
  return { message: fallback };
}

export const notify = {
  success: (message: string, description?: string) => toast.success(message, { description }),
  info: (message: string, description?: string) => toast.info(message, { description }),
  warning: (message: string, description?: string) => toast.warning(message, { description }),
  /** Accepts a string or any thrown error; API errors show the request id for support. */
  error: (errOrMessage: unknown, fallback = "Something went wrong") => {
    if (typeof errOrMessage === "string") return toast.error(errOrMessage);
    const { message, requestId } = describe(errOrMessage, fallback);
    return toast.error(message, { description: requestId ? `Reference: ${requestId}` : undefined });
  },
  /** Loading → success/error toast that follows a promise. */
  promise: <T>(p: Promise<T>, msgs: { loading: string; success: string; error?: string }) =>
    toast.promise(p, {
      loading: msgs.loading,
      success: msgs.success,
      error: (e: unknown) => describe(e, msgs.error ?? "Something went wrong").message,
    }),
};
