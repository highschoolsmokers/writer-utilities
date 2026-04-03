import { checkSubmissionStatus } from "./lib/check-submissions.mjs";
import { sendNotification } from "./lib/notify.mjs";
import { redis } from "../api/_lib/redis.mjs";

const STATE_KEY = "one-story:last-status";
const NOTIFIED_KEY = "one-story:notified";

export async function run() {
  const status = await checkSubmissionStatus();
  await redis.set(STATE_KEY, JSON.stringify(status));

  if (status.open) {
    const alreadyNotified = await redis.get(NOTIFIED_KEY);
    if (!alreadyNotified) {
      const to = process.env.NOTIFY_EMAIL;
      if (to) {
        await sendNotification({ to, status });
        await redis.set(NOTIFIED_KEY, "true", 60 * 60 * 24 * 30);
        return { agent: "one-story-watcher", ...status, notified: to };
      }
    }
    return { agent: "one-story-watcher", ...status, notified: "already sent" };
  }

  return { agent: "one-story-watcher", ...status };
}
