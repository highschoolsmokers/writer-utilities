import fs from "node:fs/promises";
import path from "node:path";

export async function extractText(filePath: string): Promise<string> {
  const ext = path.extname(filePath).toLowerCase();
  const buf = await fs.readFile(filePath);

  switch (ext) {
    case ".txt":
      return buf.toString("utf-8");

    case ".rtf":
      return stripRtf(buf.toString("utf-8"));

    case ".docx": {
      const mammoth = await import("mammoth");
      const result = await mammoth.extractRawText({ buffer: buf });
      return result.value;
    }

    default:
      throw new Error(`Unsupported file format: ${ext}`);
  }
}

function stripRtf(rtf: string): string {
  let text = rtf.replace(
    /\{\\(?:fonttbl|colortbl|stylesheet|info|pict)[^}]*\}/g,
    "",
  );
  text = text.replace(/\\[a-z]+\d*\s?/gi, "");
  text = text.replace(/\\'[0-9a-f]{2}/gi, "");
  text = text.replace(/[{}]/g, "");
  text = text.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
  text = text.replace(/\n{3,}/g, "\n\n");
  return text.trim();
}

export function extractTitle(text: string): string {
  const lines = text.split("\n");
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    const prefixed = trimmed.match(/^title:\s*(.+)$/i);
    if (prefixed) return prefixed[1].trim();
    return trimmed;
  }
  return "Untitled";
}

export function countWords(text: string): number {
  return text.split(/\s+/).filter((w) => w.length > 0).length;
}

export function roundWordCount(count: number): number {
  return Math.round(count / 100) * 100;
}
