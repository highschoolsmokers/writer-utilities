#!/usr/bin/env node
import { checkSubmissionStatus } from "./lib/check-submissions.mjs";

async function main() {
  console.log("Checking One Story Submittable page...\n");
  try {
    const status = await checkSubmissionStatus();
    if (status.open) {
      console.log("SUBMISSIONS ARE OPEN");
      console.log("    https://one-story.submittable.com/submit\n");
    } else {
      console.log("Submissions closed.\n");
    }
    console.log(`    Checked: ${status.checkedAt}`);
    console.log(`    Slugs:   ${status.opportunities.join(", ") || "(none)"}`);
  } catch (err) {
    console.error("Error:", err.message);
    process.exit(1);
  }
}

main();
