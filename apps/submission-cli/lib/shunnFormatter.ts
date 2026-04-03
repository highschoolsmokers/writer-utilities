import PDFDocument from "pdfkit";
import { roundWordCount } from "./manuscriptParser.js";

const W = 612;
const H = 792;
const MARGIN = 72;
const CONTENT_W = W - 2 * MARGIN;
const CONTENT_H = H - 2 * MARGIN;

const FONT = "Courier";
const FONT_SIZE = 12;
const LINE_HEIGHT = 24;
const INDENT = 36;
const HEADER_Y = 36;

const BODY_TOP = MARGIN;
const LINES_PER_PAGE = Math.floor(CONTENT_H / LINE_HEIGHT);

const SCENE_BREAK_RE = /^(?:#|#{3}|\*{3}|-{3}|~{3}|\* \* \*)$/;

interface ManuscriptParams {
  text: string;
  title: string;
  authorName: string;
  authorAddress: string;
  authorEmail: string;
  authorPhone?: string;
  wordCount: number;
  penName?: string;
}

type Doc = InstanceType<typeof PDFDocument>;

export async function renderManuscript(
  params: ManuscriptParams,
): Promise<Buffer> {
  return new Promise((resolve, reject) => {
    const doc = new PDFDocument({
      size: "letter",
      margins: { top: MARGIN, bottom: MARGIN, left: MARGIN, right: MARGIN },
      bufferPages: true,
    });

    const chunks: Buffer[] = [];
    doc.on("data", (chunk: Buffer) => chunks.push(chunk));
    doc.on("end", () => resolve(Buffer.concat(chunks)));
    doc.on("error", reject);

    const byline = params.penName || params.authorName;
    const surname = params.authorName.split(" ").pop() || params.authorName;
    const titleKeyword = params.title
      .split(/\s+/)
      .slice(0, 2)
      .join(" ")
      .toUpperCase();
    const approxWords = roundWordCount(params.wordCount);

    // Title page
    let y = MARGIN;
    doc.font(FONT).fontSize(FONT_SIZE);

    const contactLines = [
      params.authorName,
      params.authorAddress,
      params.authorEmail,
    ];
    if (params.authorPhone) contactLines.push(params.authorPhone);

    for (const line of contactLines) {
      doc.text(line, MARGIN, y, { lineBreak: false });
      y += FONT_SIZE + 2;
    }

    const wordCountText = `about ${approxWords.toLocaleString()} words`;
    const wcWidth = doc.widthOfString(wordCountText);
    doc.text(wordCountText, W - MARGIN - wcWidth, MARGIN, { lineBreak: false });

    const centerY = H / 3 + 36;
    doc.text(params.title, MARGIN, centerY, {
      width: CONTENT_W,
      align: "center",
    });
    doc.text("", MARGIN, centerY + LINE_HEIGHT);
    doc.text(`by ${byline}`, MARGIN, centerY + LINE_HEIGHT * 2, {
      width: CONTENT_W,
      align: "center",
    });

    // Body pages
    const paragraphs = parseParagraphs(params.text);
    let pageNum = 1;
    let lineCount = 0;

    function startBodyPage() {
      doc.addPage();
      pageNum++;
      lineCount = 0;
      const header = `${surname} / ${titleKeyword} / ${pageNum}`;
      const headerWidth = doc
        .font(FONT)
        .fontSize(FONT_SIZE)
        .widthOfString(header);
      doc.text(header, W - MARGIN - headerWidth, HEADER_Y, {
        lineBreak: false,
      });
    }

    function currentY(): number {
      return BODY_TOP + lineCount * LINE_HEIGHT;
    }

    function needsNewPage(): boolean {
      return lineCount >= LINES_PER_PAGE;
    }

    function writeLine(text: string, indent: boolean = false) {
      if (needsNewPage()) startBodyPage();
      const x = indent ? MARGIN + INDENT : MARGIN;
      doc.font(FONT).fontSize(FONT_SIZE);
      doc.text(text, x, currentY(), {
        width: indent ? CONTENT_W - INDENT : CONTENT_W,
        lineBreak: false,
      });
      lineCount++;
    }

    function blankLine() {
      if (needsNewPage()) startBodyPage();
      lineCount++;
    }

    startBodyPage();

    for (const para of paragraphs) {
      if (para.type === "break") {
        blankLine();
        writeLine("#");
        doc.font(FONT).fontSize(FONT_SIZE);
        doc.text("#", MARGIN, currentY() - LINE_HEIGHT, {
          width: CONTENT_W,
          align: "center",
          lineBreak: false,
        });
        blankLine();
        continue;
      }

      const lines = wrapText(doc, para.text, CONTENT_W - INDENT);
      for (let li = 0; li < lines.length; li++) {
        writeLine(lines[li], li === 0);
      }
    }

    blankLine();
    doc.font(FONT).fontSize(FONT_SIZE);
    if (needsNewPage()) startBodyPage();
    doc.text("###", MARGIN, currentY(), {
      width: CONTENT_W,
      align: "center",
      lineBreak: false,
    });

    doc.end();
  });
}

interface Paragraph {
  type: "text" | "break";
  text: string;
}

function parseParagraphs(text: string): Paragraph[] {
  const blocks = text
    .replace(/\r\n/g, "\n")
    .replace(/\r/g, "\n")
    .split(/\n\n+/);

  const result: Paragraph[] = [];
  for (const block of blocks) {
    const trimmed = block.trim();
    if (!trimmed) continue;
    if (SCENE_BREAK_RE.test(trimmed)) {
      result.push({ type: "break", text: "#" });
    } else {
      const cleaned = trimmed.replace(/\n/g, " ").replace(/\s+/g, " ");
      result.push({ type: "text", text: cleaned });
    }
  }
  return result;
}

function wrapText(doc: Doc, text: string, maxWidth: number): string[] {
  doc.font(FONT).fontSize(FONT_SIZE);
  const words = text.split(" ");
  const lines: string[] = [];
  let current = "";

  for (const word of words) {
    const test = current ? `${current} ${word}` : word;
    if (doc.widthOfString(test) <= maxWidth) {
      current = test;
    } else {
      if (current) lines.push(current);
      current = word;
    }
  }
  if (current) lines.push(current);
  return lines.length > 0 ? lines : [""];
}
