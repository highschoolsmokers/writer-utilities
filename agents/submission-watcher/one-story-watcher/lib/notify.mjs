export async function sendNotification({ to, status }) {
  const resendKey = process.env.RESEND_API_KEY;

  if (!resendKey) {
    console.log("[one-story] No RESEND_API_KEY. Console only:");
    console.log("  ONE STORY SUBMISSIONS ARE OPEN");
    console.log("  https://one-story.submittable.com/submit");
    return { method: "console" };
  }

  const res = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${resendKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      from: process.env.RESEND_FROM || "One Story Watcher <onboarding@resend.dev>",
      to: [to],
      subject: "One Story submissions are OPEN",
      html: `<div style="font-family: Georgia, serif; max-width: 480px; margin: 0 auto; padding: 40px 20px;">
        <h2 style="font-size: 18px; font-weight: normal; margin-bottom: 24px;">One Story is accepting submissions.</h2>
        <p style="line-height: 1.6; color: #333;">The magazine submission link just appeared on Submittable. They cap at 2,000 per period. Move fast.</p>
        <p style="margin-top: 24px;"><a href="https://one-story.submittable.com/submit" style="display: inline-block; padding: 12px 24px; background: #111; color: #fff; text-decoration: none; font-size: 14px;">Submit now</a></p>
        <p style="margin-top: 32px; font-size: 13px; color: #888;">Detected ${status.checkedAt}</p>
      </div>`,
    }),
  });

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Resend error: ${res.status} - ${err}`);
  }

  return { method: "email", to };
}
