from typing import Any, Callable, Optional
import uuid


class CampaignService:
    def __init__(
        self,
        *,
        now_iso: Callable[[], str],
        json_response: Callable[[int, dict], dict],
        query_bucket: Callable[[str], list[dict]],
        get_by_id: Callable[[str, Any], Optional[dict]],
        put_entity: Callable[..., dict],
        update_by_id: Callable[..., Any],
        audit_event: Callable[[str, Optional[dict], Optional[dict], Optional[dict]], None],
    ) -> None:
        self.now_iso = now_iso
        self.json_response = json_response
        self.query_bucket = query_bucket
        self.get_by_id = get_by_id
        self.put_entity = put_entity
        self.update_by_id = update_by_id
        self.audit_event = audit_event

    def campaign_payload(self, item: dict) -> dict:
        return {
            "id": item.get("campaignId"),
            "name": item.get("name") or "",
            "active": bool(item.get("active", True)),
            "hook": item.get("hook") or "",
            "description": item.get("description") or "",
            "story": item.get("story") or "",
            "feed": item.get("feed") or "",
            "banner": item.get("banner") or "",
            "heroImage": item.get("heroImage") or "",
            "heroBadge": item.get("heroBadge") or "",
            "heroTitle": item.get("heroTitle") or "",
            "heroAccent": item.get("heroAccent") or "",
            "heroTail": item.get("heroTail") or "",
            "heroDescription": item.get("heroDescription") or "",
            "ctaPrimaryText": item.get("ctaPrimaryText") or "",
            "ctaSecondaryText": item.get("ctaSecondaryText") or "",
            "benefits": item.get("benefits") or [],
            "createdAt": item.get("createdAt"),
            "updatedAt": item.get("updatedAt"),
        }

    def save_campaign(self, payload: dict, headers: Optional[dict] = None) -> dict:
        name = str(payload.get("name") or "").strip()
        hook = str(payload.get("hook") or "").strip()
        story = str(payload.get("story") or "").strip()
        feed = str(payload.get("feed") or "").strip()
        banner = str(payload.get("banner") or "").strip()
        if not name or not hook or not story or not feed or not banner:
            return self.json_response(200, {"message": "name, hook, story, feed y banner son obligatorios", "Error": "BadRequest"})

        campaign_id = str(payload.get("id") or payload.get("campaignId") or "").strip()
        now = self.now_iso()
        benefits = payload.get("benefits") if isinstance(payload.get("benefits"), list) else []

        if campaign_id and self.get_by_id("CAMPAIGN", campaign_id):
            updated = self.update_by_id(
                "CAMPAIGN",
                campaign_id,
                "SET #n = :n, active = :a, hook = :h, description = :d, story = :s, feed = :f, banner = :b, heroImage = :hi, heroBadge = :hb, heroTitle = :ht, heroAccent = :ha, heroTail = :htl, heroDescription = :hd, ctaPrimaryText = :cp, ctaSecondaryText = :cs, benefits = :be, updatedAt = :u",
                {
                    ":n": name,
                    ":a": bool(payload.get("active", True)),
                    ":h": hook,
                    ":d": str(payload.get("description") or "").strip(),
                    ":s": story,
                    ":f": feed,
                    ":b": banner,
                    ":hi": str(payload.get("heroImage") or "").strip(),
                    ":hb": str(payload.get("heroBadge") or "").strip(),
                    ":ht": str(payload.get("heroTitle") or "").strip(),
                    ":ha": str(payload.get("heroAccent") or "").strip(),
                    ":htl": str(payload.get("heroTail") or "").strip(),
                    ":hd": str(payload.get("heroDescription") or "").strip(),
                    ":cp": str(payload.get("ctaPrimaryText") or "").strip(),
                    ":cs": str(payload.get("ctaSecondaryText") or "").strip(),
                    ":be": benefits,
                    ":u": now,
                },
                ean={"#n": "name"},
            )
            self.audit_event("campaign.update", headers, payload, {"campaignId": campaign_id})
            return self.json_response(200, {"campaign": self.campaign_payload(updated)})

        campaign_id = campaign_id or f"CMP-{uuid.uuid4().hex[:10].upper()}"
        item = {
            "entityType": "campaign",
            "campaignId": campaign_id,
            "name": name,
            "active": bool(payload.get("active", True)),
            "hook": hook,
            "description": str(payload.get("description") or "").strip(),
            "story": story,
            "feed": feed,
            "banner": banner,
            "heroImage": str(payload.get("heroImage") or "").strip(),
            "heroBadge": str(payload.get("heroBadge") or "").strip(),
            "heroTitle": str(payload.get("heroTitle") or "").strip(),
            "heroAccent": str(payload.get("heroAccent") or "").strip(),
            "heroTail": str(payload.get("heroTail") or "").strip(),
            "heroDescription": str(payload.get("heroDescription") or "").strip(),
            "ctaPrimaryText": str(payload.get("ctaPrimaryText") or "").strip(),
            "ctaSecondaryText": str(payload.get("ctaSecondaryText") or "").strip(),
            "benefits": benefits,
            "createdAt": now,
            "updatedAt": now,
        }
        saved = self.put_entity("CAMPAIGN", campaign_id, item, created_at_iso=now)
        self.audit_event("campaign.create", headers, payload, {"campaignId": campaign_id})
        return self.json_response(201, {"campaign": self.campaign_payload(saved)})

    def list_campaigns(self) -> list[dict]:
        return [self.campaign_payload(item) for item in self.query_bucket("CAMPAIGN") if isinstance(item, dict)]

    def list_active_campaigns(self) -> list[dict]:
        campaigns = []
        for item in self.query_bucket("CAMPAIGN"):
            if not isinstance(item, dict):
                continue
            payload = self.campaign_payload(item)
            if not payload.get("active", True):
                continue
            campaigns.append(payload)
        return campaigns


__all__ = ["CampaignService"]
