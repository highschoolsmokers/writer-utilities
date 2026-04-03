# one-story-watcher

Polls One Story Submittable page and emails you the moment magazine submissions open.

One Story caps at 2,000 submissions per period and closes when full. This agent detects the magazine submission link (slug: one-story) on their Submittable page, distinct from workshops, conferences, and teen submissions, and sends a single notification per opening via Resend.

## Local test

node one-story-watcher/check-local.mjs

## Detection logic

When closed, the Submittable page only lists workshops, conferences, teen, and scholarship submissions. When open, a slug matching one-story appears. The agent catches that distinction.
