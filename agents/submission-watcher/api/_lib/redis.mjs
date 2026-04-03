function getConfig() {
  const url = process.env.UPSTASH_REDIS_REST_URL;
  const token = process.env.UPSTASH_REDIS_REST_TOKEN;
  return { url, token, configured: !!(url && token) };
}

async function request(path) {
  const { url, token, configured } = getConfig();
  if (!configured) return null;
  const res = await fetch(`${url}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) return null;
  const data = await res.json();
  return data.result;
}

export const redis = {
  async get(key) {
    return request(`/get/${encodeURIComponent(key)}`);
  },
  async set(key, value, exSeconds) {
    const path = exSeconds
      ? `/set/${encodeURIComponent(key)}/${encodeURIComponent(value)}/ex/${exSeconds}`
      : `/set/${encodeURIComponent(key)}/${encodeURIComponent(value)}`;
    return request(path);
  },
  async del(key) {
    return request(`/del/${encodeURIComponent(key)}`);
  },
};
