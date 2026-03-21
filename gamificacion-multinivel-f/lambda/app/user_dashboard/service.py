from decimal import Decimal
from typing import Any, Callable, Optional


class UserDashboardService:
    def __init__(
        self,
        *,
        to_decimal: Callable[[Any], Decimal],
        decimal_one: Decimal,
        default_sponsor_name: str,
        default_sponsor_email: str,
        default_sponsor_phone: str,
        get_by_id: Callable[[str, Any], Optional[dict]],
        normalize_email: Callable[[Optional[str]], str],
        normalize_asset_url: Callable[[Optional[str]], str],
        truthy_flag: Callable[[Any, bool], bool],
    ) -> None:
        self.to_decimal = to_decimal
        self.decimal_one = decimal_one
        self.default_sponsor_name = default_sponsor_name
        self.default_sponsor_email = default_sponsor_email
        self.default_sponsor_phone = default_sponsor_phone
        self.get_by_id = get_by_id
        self.normalize_email = normalize_email
        self.normalize_asset_url = normalize_asset_url
        self.truthy_flag = truthy_flag

    def build_settings_payload(self, user_id: Any, is_guest: bool) -> dict:
        return {
            "cutoffDay": 25,
            "cutoffHour": 23,
            "cutoffMinute": 59,
            "userCode": "" if is_guest else str(user_id),
            "networkGoal": 300,
        }

    def build_user_payload(self, customer: Optional[dict]) -> Optional[dict]:
        if not customer or not isinstance(customer, dict):
            return None

        discount_rate = self.to_decimal(customer.get("discountRate"))
        return {
            "discountPercent": int((discount_rate * 100).quantize(self.decimal_one)) if discount_rate else 0,
            "discountActive": bool(customer.get("activeBuyer") or discount_rate > 0),
        }

    def build_sponsor_payload(self, customer: Optional[dict]) -> dict:
        if not customer or not isinstance(customer, dict):
            return self.sponsor_contact_payload(None)

        sponsor_id = customer.get("leaderId")
        sponsor = self.get_by_id("CUSTOMER", int(sponsor_id)) if sponsor_id not in (None, "") else None
        return self.sponsor_contact_payload(sponsor)

    def sponsor_contact_payload(self, customer: Optional[dict]) -> dict:
        return self._sponsor_contact_payload(customer)

    def build_products_payload(self, products_raw: list[dict]) -> tuple[list[dict], list[dict]]:
        products = []
        featured = []

        for item in products_raw:
            if not self.is_product_active(item):
                continue

            summary = self.product_summary(item)
            products.append(
                {
                    "id": summary["id"],
                    "name": summary["name"],
                    "price": summary["price"],
                    "badge": summary["badge"],
                    "img": summary["img"],
                    "description": summary["description"],
                    "copyFacebook": summary["copyFacebook"],
                    "copyInstagram": summary["copyInstagram"],
                    "copyWhatsapp": summary["copyWhatsapp"],
                }
            )

            if len(featured) >= 4:
                continue

            images = item.get("images") or []
            featured.append(
                {
                    "id": summary["id"],
                    "label": summary["name"],
                    "hook": summary["hook"],
                    "story": self.pick_product_image(images, ["redes"]) or summary["img"],
                    "feed": self.pick_product_image(images, ["miniatura", "redes"]) or summary["img"],
                    "banner": self.pick_product_image(images, ["landing"]) or summary["img"],
                }
            )

        return products, featured

    def build_product_of_month_payload(self, item: Optional[dict]) -> Optional[dict]:
        if not item or not isinstance(item, dict):
            return None

        product_id = item.get("productId")
        product = self.get_by_id("PRODUCT", int(product_id)) if product_id not in (None, "") else None
        if not product or not isinstance(product, dict):
            return None
        product_item: dict = product
        if not self.is_product_active(product_item):
            return None
        return self.product_summary(product_item)

    def pick_product_image(self, images: Optional[list], preferred_sections: list[str]) -> str:
        if not images or not isinstance(images, list):
            return ""

        for section in preferred_sections:
            for image in images:
                if image.get("section") == section and image.get("url"):
                    return self.normalize_asset_url(image.get("url"))

        for image in images:
            if image.get("url"):
                return self.normalize_asset_url(image.get("url"))

        return ""

    def is_product_active(self, item: Optional[dict]) -> bool:
        if not item or not isinstance(item, dict):
            return False
        return self.truthy_flag(item.get("active"), True)

    def product_summary(self, item: dict) -> dict:
        images = item.get("images") or []
        tags = item.get("tags") or []
        badge = str(tags[0]) if tags else ""
        image = self.pick_product_image(images, ["miniatura", "landing", "redes"])
        return {
            "id": str(item.get("productId")),
            "name": item.get("name"),
            "price": float(item.get("price") or 0),
            "badge": badge,
            "img": image,
            "hook": item.get("hook") or "",
            "description": item.get("description") or "",
            "copyFacebook": item.get("copyFacebook") or "",
            "copyInstagram": item.get("copyInstagram") or "",
            "copyWhatsapp": item.get("copyWhatsapp") or "",
            "images": images,
            "tags": tags,
        }

    def _sponsor_contact_payload(self, customer: Optional[dict]) -> dict:
        if customer and isinstance(customer, dict):
            return {
                "name": (customer.get("name") or self.default_sponsor_name).strip() or self.default_sponsor_name,
                "email": self.normalize_email(customer.get("email")) or self.default_sponsor_email,
                "phone": str(customer.get("phone") or "").strip() or self.default_sponsor_phone,
                "isDefault": False,
            }
        return {
            "name": self.default_sponsor_name,
            "email": self.default_sponsor_email,
            "phone": self.default_sponsor_phone,
            "isDefault": True,
        }


__all__ = ["UserDashboardService"]
