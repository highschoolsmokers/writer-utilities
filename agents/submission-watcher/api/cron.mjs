import { run as oneStoryWatcher } from "../one-story-watcher/index.mjs";

const agents = [
  { name: "one-story-watcher", run: oneStoryWatcher },
];

export default async function handler(req, res) {
  const secret = process.env.CRON_SECRET;
  if (secret && req.headers["authorization"] !== `Bearer ${secret}`) {
    return res.status(401).json({ error: "unauthorized" });
  }

  const results = [];
  for (const agent of agents) {
    try {
      const result = await agent.run();
      results.push(result);
    } catch (err) {
      console.error(`[cron] ${agent.name} failed:`, err.message);
      results.push({ agent: agent.name, error: err.message });
    }
  }

  return res.status(200).json({ ran: agents.length, results });
}
