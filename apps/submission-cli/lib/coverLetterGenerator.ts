import Anthropic from "@anthropic-ai/sdk";

interface CoverLetterParams {
  title: string;
  wordCount: number;
  genre?: string;
  targetPublication: string;
  authorBio: string;
  synopsis?: string;
}

const SYSTEM_PROMPT = `You are a professional fiction writer drafting a cover letter for a literary magazine submission. Write a concise, professional cover letter body (3-4 short paragraphs). Do NOT include "Dear Editors" or a signature block — those will be added separately.

Paragraph 1: Introduce the piece — title (in quotes), word count, and genre/form.
Paragraph 2: A brief, compelling hook about the story (1-2 sentences max). If a synopsis is provided, use it. Otherwise, keep this paragraph very brief or omit it.
Paragraph 3: A short author bio paragraph, adapted from the provided bio. Mention relevant publications or credentials. Keep it under 3 sentences.
Paragraph 4 (optional): A brief, polite closing line thanking the editors for their consideration.

Keep the tone professional but warm. Avoid cliches like "I hope you enjoy" or "I believe your readers will love." Never summarize the plot in detail. Be concise — most editors prefer short cover letters.`;

export async function generateCoverLetter(
  params: CoverLetterParams,
): Promise<string> {
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    throw new Error("ANTHROPIC_API_KEY is not configured");
  }

  const client = new Anthropic({ apiKey });

  const userPrompt = [
    `Title: "${params.title}"`,
    `Word count: ${params.wordCount}`,
    params.genre ? `Genre/form: ${params.genre}` : null,
    `Target publication: ${params.targetPublication}`,
    `Author bio: ${params.authorBio}`,
    params.synopsis ? `Synopsis: ${params.synopsis}` : null,
  ]
    .filter(Boolean)
    .join("\n");

  const response = await client.messages.create({
    model: "claude-sonnet-4-20250514",
    max_tokens: 1024,
    temperature: 0.7,
    system: SYSTEM_PROMPT,
    messages: [{ role: "user", content: userPrompt }],
  });

  const block = response.content[0];
  if (block.type !== "text") {
    throw new Error("Unexpected response format from Claude API");
  }
  return block.text;
}
