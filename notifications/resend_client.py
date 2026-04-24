"""
email/resend_client.py
Sends post-activity analysis emails via the Resend API.
"""
import os
import httpx


RESEND_API_URL = "https://api.resend.com/emails"


async def send_analysis_email(
    to_email: str,
    to_name: str,
    subject: str,
    analysis_text: str,
    activity: dict,
):
    """Send a clean HTML analysis email via Resend."""
    html = _build_email_html(to_name, analysis_text, activity)

    payload = {
        "from": os.environ["RESEND_FROM_EMAIL"],
        "to": [to_email],
        "subject": subject,
        "html": html,
    }

    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            RESEND_API_URL,
            headers={
                "Authorization": f"Bearer {os.environ['RESEND_API_KEY']}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        r.raise_for_status()
        return r.json()


def _build_email_html(name: str, analysis: str, activity: dict) -> str:
    sport = activity.get("sport", "Workout")
    duration = activity.get("duration_min", 0)
    distance = activity.get("distance_km", 0)
    tss = activity.get("tss", "N/A")
    avg_hr = activity.get("avg_hr", "N/A")
    avg_power = activity.get("avg_power")

    stats_rows = f"""
    <tr><td>Duration</td><td>{duration} min</td></tr>
    <tr><td>Distance</td><td>{distance} km</td></tr>
    <tr><td>TSS</td><td>{tss}</td></tr>
    <tr><td>Avg HR</td><td>{avg_hr} bpm</td></tr>
    """
    if avg_power:
        stats_rows += f"<tr><td>Avg Power</td><td>{avg_power}w</td></tr>"

    # Convert analysis line breaks to <p> tags
    paragraphs = "".join(
        f"<p style='margin:0 0 12px;'>{line}</p>"
        for line in analysis.strip().split("\n")
        if line.strip()
    )

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f5;padding:32px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:8px;overflow:hidden;max-width:600px;width:100%;">
        
        <!-- Header -->
        <tr><td style="background:#111;padding:24px 32px;">
          <p style="margin:0;color:#fff;font-size:13px;letter-spacing:2px;text-transform:uppercase;">{sport}</p>
          <h1 style="margin:4px 0 0;color:#fff;font-size:22px;font-weight:600;">{activity.get('name', 'Workout Analysis')}</h1>
        </td></tr>
        
        <!-- Stats strip -->
        <tr><td style="background:#f8f8f8;padding:16px 32px;border-bottom:1px solid #eee;">
          <table cellpadding="0" cellspacing="0" style="width:100%;">
            <tr style="font-size:12px;color:#888;text-transform:uppercase;letter-spacing:1px;">
              <td>Duration</td><td>Distance</td><td>TSS</td><td>Avg HR</td>
              {"<td>Power</td>" if avg_power else ""}
            </tr>
            <tr style="font-size:20px;font-weight:600;color:#111;padding-top:4px;">
              <td>{duration}m</td>
              <td>{distance}km</td>
              <td>{tss}</td>
              <td>{avg_hr}</td>
              {f"<td>{avg_power}w</td>" if avg_power else ""}
            </tr>
          </table>
        </td></tr>
        
        <!-- Analysis body -->
        <tr><td style="padding:28px 32px;font-size:15px;line-height:1.6;color:#333;">
          <p style="margin:0 0 16px;font-size:13px;color:#888;">Hey {name},</p>
          {paragraphs}
        </td></tr>
        
        <!-- Footer -->
        <tr><td style="padding:16px 32px 24px;border-top:1px solid #eee;">
          <p style="margin:0;font-size:12px;color:#aaa;">AI Coach · Powered by Claude &amp; Intervals.icu</p>
        </td></tr>
        
      </table>
    </td></tr>
  </table>
</body>
</html>"""
