#!/usr/bin/env npx tsx
/**
 * Submission Pipeline CLI
 *
 * Usage:
 *   npx tsx submit.ts --file ~/story.txt --publication "Clarkesworld"
 *   npx tsx submit.ts --file ~/story.txt --publication "Lightspeed" --genre "science fiction"
 *   npx tsx submit.ts --scan
 *   npx tsx submit.ts --list
 *   npx tsx submit.ts --author
 */

import { parseArgs } from "node:util";
import fs from "node:fs/promises";
import path from "node:path";
import os from "node:os";
import readline from "node:readline";

import {
  extractText,
  extractTitle,
  countWords,
} from "./lib/manuscriptParser.js";
import { renderManuscript } from "./lib/shunnFormatter.js";
import { generateCoverLetter } from "./lib/coverLetterGenerator.js";
import {
  createSubmission,
  listSubmissions,
  getAuthorConfig,
  saveAuthorConfig,
  submissionDir,
  updateSubmission,
} from "./lib/queue.js";

const COMPILE_DIR = path.join(
  os.homedir(),
  "Documents",
  "Scrivener",
  "Compile",
);

const { values } = parseArgs({
  options: {
    file: { type: "string", short: "f" },
    publication: { type: "string", short: "p" },
    genre: { type: "string", short: "g" },
    scan: { type: "boolean", short: "s" },
    list: { type: "boolean", short: "l" },
    author: { type: "boolean", short: "a" },
    help: { type: "boolean", short: "h" },
  },
  strict: true,
});

function prompt(rl: readline.Interface, question: string): Promise<string> {
  return new Promise((resolve) => rl.question(question, resolve));
}

async function configureAuthor() {
  const existing = await getAuthorConfig();
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });

  console.log("\nAuthor Configuration (press Enter to keep existing value)\n");

  const name =
    (await prompt(rl, `Name [${existing?.name ?? ""}]: `)).trim() ||
    existing?.name ||
    "";
  const penName =
    (await prompt(rl, `Pen name [${existing?.penName ?? "none"}]: `)).trim() ||
    existing?.penName;
  const address =
    (await prompt(rl, `Address [${existing?.address ?? ""}]: `)).trim() ||
    existing?.address ||
    "";
  const email =
    (await prompt(rl, `Email [${existing?.email ?? ""}]: `)).trim() ||
    existing?.email ||
    "";
  const phone =
    (await prompt(rl, `Phone [${existing?.phone ?? "none"}]: `)).trim() ||
    existing?.phone;
  console.log(`Current bio: ${existing?.bio ?? "(none)"}`);
  const bioInput = (
    await prompt(rl, "Bio (one line, or Enter to keep): ")
  ).trim();
  const bio = bioInput || existing?.bio || "";

  rl.close();

  await saveAuthorConfig({ name, penName, address, email, phone, bio });
  console.log("\nAuthor config saved.");
}

async function main() {
  if (values.help) {
    console.log(`
Submission Pipeline CLI

  --file, -f <path>           Manuscript file (.txt, .rtf, .docx)
  --publication, -p <name>    Target publication name
  --genre, -g <genre>         Genre (optional)
  --scan, -s                  List files in Scrivener compile folder
  --list, -l                  List queued submissions
  --author, -a                Configure author profile
  --help, -h                  Show this help
    `);
    return;
  }

  if (values.author) {
    await configureAuthor();
    return;
  }

  if (values.scan) {
    console.log(`Scanning: ${COMPILE_DIR}\n`);
    try {
      const entries = await fs.readdir(COMPILE_DIR, { withFileTypes: true });
      const files = entries.filter(
        (e) =>
          e.isFile() &&
          [".txt", ".rtf", ".docx"].includes(
            path.extname(e.name).toLowerCase(),
          ),
      );
      if (files.length === 0) {
        console.log("No .txt/.rtf/.docx files found.");
        return;
      }
      for (const f of files) {
        const stat = await fs.stat(path.join(COMPILE_DIR, f.name));
        console.log(
          `  ${f.name}  (${(stat.size / 1024).toFixed(1)} KB, ${stat.mtime.toLocaleDateString()})`,
        );
      }
    } catch {
      console.error(`Could not read ${COMPILE_DIR}`);
    }
    return;
  }

  if (values.list) {
    const submissions = await listSubmissions();
    if (submissions.length === 0) {
      console.log("No submissions queued.");
      return;
    }
    console.log(
      `${"Title".padEnd(30)} ${"Words".padStart(6)} ${"Status".padEnd(10)} Publication`,
    );
    console.log("-".repeat(70));
    for (const s of submissions) {
      console.log(
        `${s.title.slice(0, 28).padEnd(30)} ${String(s.wordCount).padStart(6)} ${s.status.padEnd(10)} ${s.targetPublication}`,
      );
    }
    return;
  }

  if (!values.file) {
    console.error("Error: --file is required. Use --help for usage.");
    process.exit(1);
  }
  if (!values.publication) {
    console.error("Error: --publication is required. Use --help for usage.");
    process.exit(1);
  }

  const author = await getAuthorConfig();
  if (!author) {
    console.error(
      "Error: Author config not set. Run with --author to configure your profile.",
    );
    process.exit(1);
  }

  const filePath = path.resolve(values.file);
  console.log(`Reading: ${filePath}`);
  const text = await extractText(filePath);
  const title = extractTitle(text);
  const wordCount = countWords(text);
  console.log(`Title: "${title}"`);
  console.log(`Words: ${wordCount.toLocaleString()}`);

  const submission = await createSubmission({
    title,
    wordCount,
    targetPublication: values.publication,
    genre: values.genre,
    source: { type: "file", path: filePath, filename: path.basename(filePath) },
  });
  console.log(`\nSubmission ID: ${submission.id}`);

  console.log("Generating manuscript PDF...");
  const pdfBuffer = await renderManuscript({
    text,
    title,
    authorName: author.name,
    authorAddress: author.address,
    authorEmail: author.email,
    authorPhone: author.phone,
    wordCount,
    penName: author.penName,
  });
  const pdfPath = path.join(submissionDir(submission.id), "manuscript.pdf");
  await fs.writeFile(pdfPath, pdfBuffer);
  await updateSubmission(submission.id, { manuscriptPdfGenerated: true });
  console.log(`PDF saved: ${pdfPath}`);

  if (process.env.ANTHROPIC_API_KEY) {
    console.log("Generating cover letter...");
    try {
      const letter = await generateCoverLetter({
        title,
        wordCount,
        genre: values.genre,
        targetPublication: values.publication,
        authorBio: author.bio,
      });
      const letterPath = path.join(
        submissionDir(submission.id),
        "cover-letter.txt",
      );
      await fs.writeFile(letterPath, letter);
      await updateSubmission(submission.id, {
        coverLetterGenerated: true,
        status: "ready",
      });
      console.log(`Cover letter saved: ${letterPath}`);
      console.log("\n--- Cover Letter ---\n");
      console.log(letter);
    } catch (err) {
      console.error(
        "Cover letter generation failed:",
        err instanceof Error ? err.message : err,
      );
    }
  } else {
    console.log("\nSkipping cover letter (ANTHROPIC_API_KEY not set).");
  }

  console.log("\nDone. Submit manually on Submittable.");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
