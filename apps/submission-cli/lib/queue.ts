import fs from "node:fs/promises";
import path from "node:path";
import crypto from "node:crypto";
import type { Submission, AuthorConfig } from "./schema.js";

const BASE_DIR = path.join(process.cwd(), "private", "submissions");
const QUEUE_FILE = path.join(BASE_DIR, "queue.json");
const AUTHOR_FILE = path.join(BASE_DIR, "author.json");

// Simple mutex for sequential writes
let writeLock = Promise.resolve();

async function ensureDir(dir: string) {
  await fs.mkdir(dir, { recursive: true });
}

async function readQueue(): Promise<Submission[]> {
  try {
    const data = await fs.readFile(QUEUE_FILE, "utf-8");
    return JSON.parse(data);
  } catch {
    return [];
  }
}

async function writeQueue(submissions: Submission[]): Promise<void> {
  await ensureDir(BASE_DIR);
  await fs.writeFile(QUEUE_FILE, JSON.stringify(submissions, null, 2));
}

function withLock<T>(fn: () => Promise<T>): Promise<T> {
  const next = writeLock.then(fn, fn);
  writeLock = next.then(
    () => {},
    () => {},
  );
  return next;
}

export function submissionDir(id: string): string {
  return path.join(BASE_DIR, id);
}

export async function listSubmissions(): Promise<Submission[]> {
  return readQueue();
}

export async function getSubmission(
  id: string,
): Promise<Submission | undefined> {
  const queue = await readQueue();
  return queue.find((s) => s.id === id);
}

export async function createSubmission(
  data: Pick<
    Submission,
    "title" | "wordCount" | "targetPublication" | "source"
  > &
    Partial<Pick<Submission, "genre">>,
): Promise<Submission> {
  return withLock(async () => {
    const queue = await readQueue();
    const now = new Date().toISOString();
    const submission: Submission = {
      id: crypto.randomUUID(),
      title: data.title,
      wordCount: data.wordCount,
      targetPublication: data.targetPublication,
      genre: data.genre,
      status: "draft",
      source: data.source,
      manuscriptPdfGenerated: false,
      coverLetterGenerated: false,
      createdAt: now,
      updatedAt: now,
    };
    await ensureDir(submissionDir(submission.id));
    queue.push(submission);
    await writeQueue(queue);
    return submission;
  });
}

export async function updateSubmission(
  id: string,
  patch: Partial<Omit<Submission, "id" | "createdAt">>,
): Promise<Submission | undefined> {
  return withLock(async () => {
    const queue = await readQueue();
    const idx = queue.findIndex((s) => s.id === id);
    if (idx === -1) return undefined;
    queue[idx] = {
      ...queue[idx],
      ...patch,
      updatedAt: new Date().toISOString(),
    };
    await writeQueue(queue);
    return queue[idx];
  });
}

export async function deleteSubmission(id: string): Promise<boolean> {
  return withLock(async () => {
    const queue = await readQueue();
    const idx = queue.findIndex((s) => s.id === id);
    if (idx === -1) return false;
    queue.splice(idx, 1);
    await writeQueue(queue);
    try {
      await fs.rm(submissionDir(id), { recursive: true, force: true });
    } catch {
      // ignore cleanup errors
    }
    return true;
  });
}

export async function getAuthorConfig(): Promise<AuthorConfig | null> {
  try {
    const data = await fs.readFile(AUTHOR_FILE, "utf-8");
    return JSON.parse(data);
  } catch {
    return null;
  }
}

export async function saveAuthorConfig(config: AuthorConfig): Promise<void> {
  await ensureDir(BASE_DIR);
  await fs.writeFile(AUTHOR_FILE, JSON.stringify(config, null, 2));
}
