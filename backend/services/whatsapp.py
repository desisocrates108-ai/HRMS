"""WhatsApp 11za integration — sends template messages with dynamic feedback/exit
form links to candidates and exiting employees.

Template dispatch via 11za API: POST {WHATSAPP_API_URL}
Payload: {"countryCode":"+91","phoneNumber":"...", "type":"Template",
          "callbackData":"...", "language":"en",
          "myOriginWebsite":"...", "template":{"name":"...","languageCode":"en",
          "headerValues":[...], "bodyValues":[...], "buttonValues":{"0":["<url path>"]}}}
"""
import os
import logging
import httpx

logger = logging.getLogger(__name__)

# Template names — configured on 11za dashboard. Using sensible defaults; override via env.
REJECT_TEMPLATE = os.environ.get("WHATSAPP_REJECT_TEMPLATE", "candidate_feedback")
EXIT_TEMPLATE = os.environ.get("WHATSAPP_EXIT_TEMPLATE", "employee_exit_feedback")
OFFER_TEMPLATE = os.environ.get("WHATSAPP_OFFER_TEMPLATE", "offer_letter")


def _normalize_phone(phone: str) -> tuple[str, str]:
    """Return (countryCode, local_number)."""
    if not phone:
        return ("+91", "")
    p = "".join(ch for ch in phone if ch.isdigit() or ch == "+")
    if p.startswith("+"):
        return (p[:3], p[3:])
    if len(p) > 10:
        return (f"+{p[:-10]}", p[-10:])
    return ("+91", p)


async def _send_template(phone: str, template: str, body_values: list[str], button_url_path: str, callback: str):
    api_url = os.environ.get("WHATSAPP_API_URL")
    token = os.environ.get("WHATSAPP_AUTH_TOKEN")
    origin = os.environ.get("WHATSAPP_ORIGIN_WEBSITE", "")
    if not api_url or not token:
        logger.info(f"[WhatsApp] Skipped (no credentials). template={template} phone={phone}")
        return {"skipped": True, "reason": "no_credentials"}
    if not phone:
        logger.info(f"[WhatsApp] Skipped (no phone). template={template}")
        return {"skipped": True, "reason": "no_phone"}

    cc, local = _normalize_phone(phone)
    payload = {
        "countryCode": cc,
        "phoneNumber": local,
        "type": "Template",
        "callbackData": callback,
        "language": "en",
        "myOriginWebsite": origin,
        "template": {
            "name": template,
            "languageCode": "en",
            "headerValues": [],
            "bodyValues": body_values,
            "buttonValues": {"0": [button_url_path]},
        },
    }
    headers = {"Content-Type": "application/json", "Authorization": token}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(api_url, json=payload, headers=headers)
        logger.info(f"[WhatsApp] template={template} phone={phone} status={resp.status_code}")
        try:
            return {"status": resp.status_code, "body": resp.json()}
        except Exception:
            return {"status": resp.status_code, "body": resp.text[:500]}
    except Exception as e:
        logger.warning(f"[WhatsApp] Dispatch error: {e}")
        return {"error": str(e)}


def _build_feedback_url(token: str) -> str:
    base = os.environ.get("PUBLIC_APP_URL", "").rstrip("/")
    # Return the path portion (11za templates usually accept the variable URL path)
    # but if origin is the main site, we pass a full absolute URL instead.
    return f"{base}/feedback/{token}" if base else f"/feedback/{token}"


async def send_rejection_feedback(lead: dict, reason: str, feedback_token: str):
    url = _build_feedback_url(feedback_token)
    body_values = [
        lead.get("name") or "Candidate",
        reason or "thank you for your interest",
    ]
    # Pass just the path portion for 11za URL button substitution
    url_path = url.split("/feedback/")[-1]
    result = await _send_template(
        phone=lead.get("phone", ""),
        template=REJECT_TEMPLATE,
        body_values=body_values,
        button_url_path=f"feedback/{url_path}",
        callback=f"rejection:{lead.get('id', '')}",
    )
    logger.info(f"[WhatsApp] rejection link={url} result={result}")
    return result


async def send_exit_feedback(employee: dict, reason: str, feedback_token: str):
    url = _build_feedback_url(feedback_token)
    body_values = [
        employee.get("name") or "Employee",
        reason or "thank you for your service",
    ]
    url_path = url.split("/feedback/")[-1]
    result = await _send_template(
        phone=employee.get("phone", ""),
        template=EXIT_TEMPLATE,
        body_values=body_values,
        button_url_path=f"feedback/{url_path}",
        callback=f"exit:{employee.get('id', '')}",
    )
    logger.info(f"[WhatsApp] exit link={url} result={result}")
    return result


async def send_offer_letter(lead: dict, role: str, branch_name: str):
    """Dispatch a WhatsApp offer letter message on 3-month confirmation.
    Template body: {{1}}=candidate name, {{2}}=role, {{3}}=branch/department.
    """
    body_values = [
        lead.get("name") or "Candidate",
        role or "the assigned role",
        branch_name or "Servall",
    ]
    result = await _send_template(
        phone=lead.get("phone", ""),
        template=OFFER_TEMPLATE,
        body_values=body_values,
        button_url_path="offer",
        callback=f"offer:{lead.get('id', '')}",
    )
    logger.info(f"[WhatsApp] offer letter sent lead={lead.get('id')} role={role} result={result}")
    return result
