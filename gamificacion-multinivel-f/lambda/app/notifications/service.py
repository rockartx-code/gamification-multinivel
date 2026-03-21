from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
import uuid


class NotificationService:
    def __init__(
        self,
        *,
        default_link_text: str,
        max_description_length: int,
        utc_now: Callable[[], datetime],
        iso_to_dt: Callable[[Optional[str]], Optional[datetime]],
        now_iso: Callable[[], str],
        json_response: Callable[[int, dict], dict],
        query_bucket: Callable[[str], List[dict]],
        query_exact_pk: Callable[[str], List[dict]],
        resolve_actor: Callable[[Optional[dict], Optional[dict]], Any],
        get_by_id: Callable[[str, Any], Optional[dict]],
        put_entity: Callable[..., dict],
        audit_event: Callable[[str, Optional[dict], Optional[dict], Optional[dict]], None],
        parse_int_or_str: Callable[[Any], Any],
        table: Any,
    ) -> None:
        self.default_link_text = default_link_text
        self.max_description_length = max_description_length
        self.utc_now = utc_now
        self.iso_to_dt = iso_to_dt
        self.now_iso = now_iso
        self.json_response = json_response
        self.query_bucket = query_bucket
        self.query_exact_pk = query_exact_pk
        self.resolve_actor = resolve_actor
        self.get_by_id = get_by_id
        self.put_entity = put_entity
        self.audit_event = audit_event
        self.parse_int_or_str = parse_int_or_str
        self.table = table

    def notification_reads_pk(self, customer_id: Any) -> str:
        return f"NOTIFICATION_READ#{customer_id}"

    def notification_status(self, item: Optional[dict], now_dt: Optional[datetime] = None) -> str:
        if not item or not isinstance(item, dict):
            return "inactive"
        if not bool(item.get("active", True)):
            return "inactive"

        now = now_dt or self.utc_now()
        start_at = self.iso_to_dt(item.get("startAt"))
        end_at = self.iso_to_dt(item.get("endAt"))

        if start_at and start_at > now:
            return "scheduled"
        if end_at and end_at < now:
            return "expired"
        return "active"

    def notification_payload(
        self,
        item: dict,
        *,
        read_at: Optional[str] = None,
        now_dt: Optional[datetime] = None,
    ) -> dict:
        link_url = str(item.get("linkUrl") or "").strip()
        link_text = str(item.get("linkText") or "").strip()
        if link_url and not link_text:
            link_text = self.default_link_text

        return {
            "id": str(item.get("notificationId") or ""),
            "title": str(item.get("title") or "").strip(),
            "description": str(item.get("description") or "").strip(),
            "linkUrl": link_url,
            "linkText": link_text,
            "startAt": item.get("startAt"),
            "endAt": item.get("endAt"),
            "active": bool(item.get("active", True)),
            "status": self.notification_status(item, now_dt=now_dt),
            "isRead": bool(read_at),
            "readAt": read_at or "",
            "createdAt": item.get("createdAt"),
            "updatedAt": item.get("updatedAt"),
        }

    def list_notifications_for_admin(self) -> List[dict]:
        now_dt = self.utc_now()
        notifications = [
            self.notification_payload(item, now_dt=now_dt)
            for item in self.query_bucket("NOTIFICATION")
            if isinstance(item, dict)
        ]
        notifications.sort(
            key=lambda item: (
                item.get("startAt") or "",
                item.get("createdAt") or "",
                item.get("id") or "",
            ),
            reverse=True,
        )
        return notifications

    def notification_reads_for_customer(self, customer_id: Any) -> Dict[str, str]:
        if customer_id in (None, ""):
            return {}

        items = self.query_exact_pk(self.notification_reads_pk(customer_id))
        reads: Dict[str, str] = {}
        for item in items:
            notification_id = str(item.get("notificationId") or item.get("SK") or "").strip()
            if not notification_id:
                continue
            reads[notification_id] = str(item.get("readAt") or item.get("createdAt") or "").strip()
        return reads

    def active_notifications_for_customer(self, customer_id: Any) -> List[dict]:
        if customer_id in (None, ""):
            return []

        now_dt = self.utc_now()
        reads = self.notification_reads_for_customer(customer_id)
        notifications: List[dict] = []

        for item in self.query_bucket("NOTIFICATION"):
            if not isinstance(item, dict):
                continue
            notification_id = str(item.get("notificationId") or "").strip()
            if not notification_id:
                continue
            payload = self.notification_payload(item, read_at=reads.get(notification_id), now_dt=now_dt)
            if payload.get("status") != "active":
                continue
            notifications.append(payload)

        notifications.sort(
            key=lambda item: (
                item.get("startAt") or "",
                item.get("createdAt") or "",
                item.get("id") or "",
            ),
            reverse=True,
        )
        return notifications

    def save_notification(self, payload: dict, headers: Optional[dict] = None) -> dict:
        notification_id = str(payload.get("id") or payload.get("notificationId") or "").strip()
        title = str(payload.get("title") or "").strip()
        description = str(payload.get("description") or "").strip()
        link_url = str(payload.get("linkUrl") or payload.get("link") or payload.get("url") or "").strip()
        link_text = str(payload.get("linkText") or "").strip()
        start_at = str(payload.get("startAt") or "").strip()
        end_at = str(payload.get("endAt") or "").strip()
        active = bool(payload.get("active", True))

        if not title:
            return self.json_response(200, {"message": "title es obligatorio", "Error": "BadRequest"})
        if not description:
            return self.json_response(200, {"message": "description es obligatoria", "Error": "BadRequest"})
        if len(description) > self.max_description_length:
            return self.json_response(
                200,
                {
                    "message": f"description no puede exceder {self.max_description_length} caracteres",
                    "Error": "BadRequest",
                },
            )
        if not start_at or not end_at:
            return self.json_response(200, {"message": "startAt y endAt son obligatorios", "Error": "BadRequest"})

        start_dt = self.iso_to_dt(start_at)
        end_dt = self.iso_to_dt(end_at)
        if not start_dt or not end_dt:
            return self.json_response(200, {"message": "startAt o endAt tienen formato invalido", "Error": "BadRequest"})
        if end_dt < start_dt:
            return self.json_response(200, {"message": "endAt debe ser mayor o igual a startAt", "Error": "BadRequest"})

        if link_url and not link_text:
            link_text = self.default_link_text
        if not link_url:
            link_text = ""

        actor_user_id, actor_name, _ = self.resolve_actor(headers, payload)
        now = self.now_iso()
        existing = self.get_by_id("NOTIFICATION", notification_id) if notification_id else None

        if notification_id and not existing:
            return self.json_response(200, {"message": "Notificacion no encontrada", "Error": "NoEncontrado"})

        if existing:
            item = dict(existing)
            item.update(
                {
                    "title": title,
                    "description": description,
                    "linkUrl": link_url,
                    "linkText": link_text,
                    "startAt": start_at,
                    "endAt": end_at,
                    "active": active,
                    "updatedAt": now,
                    "updatedByUserId": actor_user_id,
                    "updatedByName": actor_name,
                }
            )
            self.table.put_item(Item=item)
            status_code = 200
            audit_action = "notification.update"
            saved = item
        else:
            notification_id = notification_id or f"NTF-{uuid.uuid4().hex[:12].upper()}"
            item = {
                "entityType": "notification",
                "notificationId": notification_id,
                "title": title,
                "description": description,
                "linkUrl": link_url,
                "linkText": link_text,
                "startAt": start_at,
                "endAt": end_at,
                "active": active,
                "createdByUserId": actor_user_id,
                "createdByName": actor_name,
                "updatedByUserId": actor_user_id,
                "updatedByName": actor_name,
                "createdAt": now,
                "updatedAt": now,
            }
            saved = self.put_entity("NOTIFICATION", notification_id, item, created_at_iso=now)
            status_code = 201
            audit_action = "notification.create"

        self.audit_event(audit_action, headers, payload, {"notificationId": notification_id})
        return self.json_response(status_code, {"notification": self.notification_payload(saved, now_dt=self.utc_now())})

    def mark_notification_read(self, notification_id: str, payload: dict, headers: Optional[dict] = None) -> dict:
        notification_id = str(notification_id or "").strip()
        if not notification_id:
            return self.json_response(200, {"message": "notificationId es obligatorio", "Error": "BadRequest"})

        notification = self.get_by_id("NOTIFICATION", notification_id)
        if not notification:
            return self.json_response(200, {"message": "Notificacion no encontrada", "Error": "NoEncontrado"})

        customer_id = self.parse_int_or_str(
            payload.get("customerId")
            or payload.get("userId")
            or (headers or {}).get("x-user-id")
            or (headers or {}).get("X-User-Id")
        )
        if customer_id in (None, ""):
            return self.json_response(200, {"message": "customerId es obligatorio", "Error": "BadRequest"})

        customer = self.get_by_id("CUSTOMER", int(customer_id)) if isinstance(customer_id, int) else self.get_by_id("CUSTOMER", customer_id)
        if not customer:
            return self.json_response(200, {"message": "Customer no encontrado", "Error": "NoEncontrado"})

        pk = self.notification_reads_pk(customer_id)
        existing = self.table.get_item(Key={"PK": pk, "SK": notification_id}).get("Item")
        if existing:
            return self.json_response(
                200,
                {
                    "ok": True,
                    "notificationId": notification_id,
                    "customerId": customer_id,
                    "readAt": existing.get("readAt") or existing.get("createdAt") or "",
                },
            )

        now = self.now_iso()
        item = {
            "PK": pk,
            "SK": notification_id,
            "entityType": "notificationRead",
            "notificationId": notification_id,
            "customerId": customer_id,
            "readAt": now,
            "createdAt": now,
            "updatedAt": now,
        }
        self.table.put_item(Item=item)
        self.audit_event("notification.read", headers, payload, {"notificationId": notification_id, "customerId": customer_id})
        return self.json_response(200, {"ok": True, "notificationId": notification_id, "customerId": customer_id, "readAt": now})
