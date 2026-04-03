import { redis } from "./_lib/redis.mjs";

export default async function handler(req, res) {
  try {
    const oneStory = await redis.get("one-story:last-status");
    const oneStoryNotified = await redis.get("one-story:notified");
    return res.status(200).json({
      "one-story-watcher": {
        lastCheck: oneStory ? JSON.parse(oneStory) : null,
        notified: !!oneStoryNotified,
      },
    });
  } catch (err) {
    return res.status(500).json({ error: err.message });
  }
}
