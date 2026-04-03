export interface AuthorConfig {
  name: string;
  penName?: string;
  address: string;
  email: string;
  phone?: string;
  bio: string;
}

export type SubmissionStatus = "draft" | "ready" | "submitted";

export interface SubmissionSource {
  type: "file" | "paste";
  path?: string;
  filename?: string;
}

export interface Submission {
  id: string;
  title: string;
  wordCount: number;
  targetPublication: string;
  genre?: string;
  status: SubmissionStatus;
  source: SubmissionSource;
  manuscriptPdfGenerated: boolean;
  coverLetterGenerated: boolean;
  createdAt: string;
  updatedAt: string;
}
