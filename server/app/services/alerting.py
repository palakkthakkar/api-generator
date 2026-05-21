"""
Sends alerts when anomalies are detected.
Supports Slack webhooks and email (via SMTP).
"""

import json
import httpx
import smtplib
from email.mime.text import MIMEText
from ..config import settings


async def send_slack_alert(webhook_url: str, anomaly: dict, endpoint: str):
    """Send a formatted Slack message about a detected anomaly."""
    severity_emoji = "🔴" if anomaly["severity"] > 0.7 else "🟡"
    top_features = anomaly["autoencoder"]["top_contributing_features"]
    feature_text = "\n".join(
        f"  • {f['feature']}: deviation {f['deviation']:.3f}"
        for f in top_features
    )

    message = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{severity_emoji} Anomaly Detected — {endpoint}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*Severity:* {anomaly['severity']:.0%}\n"
                        f"*Score:* {anomaly['autoencoder']['anomaly_score']:.4f} "
                        f"(threshold: {anomaly['autoencoder']['threshold']:.4f})\n"
                        f"*Top deviating features:*\n{feature_text}"
                    )
                }
            }
        ]
    }

    async with httpx.AsyncClient() as client:
        await client.post(webhook_url, json=message)


def send_email_alert(to_email: str, anomaly: dict, endpoint: str):
    """Send email alert via SMTP."""
    subject = f"[SentinelAPI] Anomaly on {endpoint} — severity {anomaly['severity']:.0%}"
    body = (
        f"Anomaly detected on endpoint: {endpoint}\n"
        f"Severity: {anomaly['severity']:.0%}\n"
        f"Anomaly score: {anomaly['autoencoder']['anomaly_score']:.4f}\n"
        f"Top features: {json.dumps(anomaly['autoencoder']['top_contributing_features'], indent=2)}\n"
    )
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["To"] = to_email

    # Configure SMTP in .env for production
    # For demo, just print
    print(f"[Email Alert] {subject}\n{body}")