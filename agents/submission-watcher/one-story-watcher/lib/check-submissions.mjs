const SUBMITTABLE_URL = "https://one-story.submittable.com/submit";

export async function checkSubmissionStatus() {
  const res = await fetch(SUBMITTABLE_URL, {
    headers: {
      "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
      Accept: "text/html",
    },
  });

  if (!res.ok) {
    throw new Error(`Submittable returned ${res.status}`);
  }

  const html = await res.text();

  const nonMagazinePatterns = [
    /conference/i, /workshop/i, /teen\s*story/i,
    /scholarship/i, /lecture/i, /reading\s*group/i, /class/i,
  ];

  const opportunityRegex = /\/submit\/(\d+)\/([^"'\s]+)/gi;
  const opportunities = [];
  let match;
  while ((match = opportunityRegex.exec(html)) !== null) {
    opportunities.push({ id: match[1], slug: match[2] });
  }

  const seen = new Set();
  const unique = opportunities.filter((o) => {
    const key = `${o.id}-${o.slug}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });

  const hasMagazineSubmission =
    unique.some((o) => /^one-story$/i.test(o.slug)) ||
    /submit\s+to\s+one\s+story(?!\s*(?:writers|summer|teen|conference|workshop))/i.test(html);

  return {
    open: hasMagazineSubmission,
    checkedAt: new Date().toISOString(),
    opportunities: unique.map((o) => o.slug),
  };
}
