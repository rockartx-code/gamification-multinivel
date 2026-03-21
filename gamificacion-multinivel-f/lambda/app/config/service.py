import functools
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional


class ConfigService:
    def __init__(
        self,
        *,
        default_commission_by_depth: Dict[int, Decimal],
        json_response: Callable[[int, dict], dict],
        audit_event: Callable[[str, Optional[dict], Optional[dict], Optional[dict]], None],
        get_by_id: Callable[[str, Any], Optional[dict]],
        put_entity: Callable[..., dict],
        update_by_id: Callable[..., Any],
        now_iso: Callable[[], str],
        to_decimal: Callable[[Any], Decimal],
    ) -> None:
        self.default_commission_by_depth = default_commission_by_depth
        self.json_response = json_response
        self.audit_event = audit_event
        self.get_by_id = get_by_id
        self.put_entity = put_entity
        self.update_by_id = update_by_id
        self.now_iso = now_iso
        self.to_decimal = to_decimal
        self._load_app_config_cached = functools.lru_cache(maxsize=1)(self._load_app_config_cached_impl)

    def default_rewards_config(self) -> dict:
        return {
            "version": "v1",
            "activationNetMin": Decimal("2500"),
            "discountTiers": [
                {"min": Decimal("3600"), "max": Decimal("8000"), "rate": Decimal("0.30")},
                {"min": Decimal("8001"), "max": Decimal("12000"), "rate": Decimal("0.40")},
                {"min": Decimal("12001"), "max": None, "rate": Decimal("0.50")},
            ],
            "commissionByDepth": {
                "1": Decimal("0.10"),
                "2": Decimal("0.05"),
                "3": Decimal("0.03"),
            },
            "payoutDay": Decimal("10"),
            "cutRule": "hard_cut_no_pass",
        }

    def default_app_config(self) -> dict:
        return {
            "version": "app-v1",
            "rewards": self.default_rewards_config(),
            "orders": {
                "requireStockOnShipped": True,
                "requireDispatchLinesOnShipped": True,
            },
            "pos": {
                "defaultCustomerName": "Publico en General",
                "defaultPaymentStatus": "paid_branch",
                "defaultDeliveryStatus": "delivered_branch",
                "orderStatusByDeliveryStatus": {
                    "delivered_branch": "delivered",
                    "paid_branch": "paid",
                },
            },
            "stocks": {
                "requireLinkedUserForTransferReceive": True,
            },
            "payments": {
                "mercadoLibre": {
                    "enabled": False,
                    "accessToken": "",
                    "checkoutPreferencesUrl": "https://api.mercadopago.com/checkout/preferences",
                    "paymentInfoUrlTemplate": "https://api.mercadopago.com/v1/payments/{payment_id}",
                    "notificationUrl": "https://m85v7secp8.execute-api.us-east-1.amazonaws.com/default/Multinivel/webhooks/mercadolibre",
                    "successUrl": "https://www.findingu.com.mx/#/orden/{payment_id}?status=success",
                    "failureUrl": "https://www.findingu.com.mx/#/orden/{payment_id}?status=failure",
                    "pendingUrl": "https://www.findingu.com.mx/#/orden/{payment_id}?status=pending",
                    "currencyId": "MXN",
                    "webhookSecret": "",
                },
            },
            "adminWarnings": {
                "showCommissions": True,
                "showShipping": True,
                "showPendingPayments": True,
                "showPendingTransfers": True,
                "showPosSalesToday": True,
            },
        }

    def legacy_rewards_config_entity_id(self) -> str:
        return "rewards-v1"

    def app_config_entity_id(self) -> str:
        return "app-v1"

    def merge_dict(self, base: Any, override: Any) -> Any:
        if isinstance(base, dict) and isinstance(override, dict):
            merged = dict(base)
            for key, value in override.items():
                merged[key] = self.merge_dict(merged.get(key), value)
            return merged
        return override if override is not None else base

    def ensure_commission_by_depth(self, cfg: dict) -> dict:
        mapping = cfg.get("commissionByDepth") if isinstance(cfg, dict) else None
        if not isinstance(mapping, dict):
            mapping = {}
        normalized = dict(cfg or {})
        normalized["commissionByDepth"] = {
            "1": self.to_decimal(mapping.get("1", mapping.get(1, self.default_commission_by_depth[1]))),
            "2": self.to_decimal(mapping.get("2", mapping.get(2, self.default_commission_by_depth[2]))),
            "3": self.to_decimal(mapping.get("3", mapping.get(3, self.default_commission_by_depth[3]))),
        }
        return normalized

    def normalize_rewards_config(self, raw: Any) -> dict:
        base = self.default_rewards_config()
        merged = self.merge_dict(base, raw if isinstance(raw, dict) else {})
        cfg = self.ensure_commission_by_depth(merged)
        tiers_raw = cfg.get("discountTiers") or []
        tiers: List[dict] = []
        for tier in tiers_raw:
            if not isinstance(tier, dict):
                continue
            min_value = self.to_decimal(tier.get("min"))
            max_raw = tier.get("max")
            max_value = self.to_decimal(max_raw) if max_raw not in (None, "") else None
            rate = self.to_decimal(tier.get("rate"))
            tiers.append({"min": min_value, "max": max_value, "rate": rate})
        if not tiers:
            tiers = base.get("discountTiers") or []
        cbd = cfg.get("commissionByDepth") or {}
        return {
            "version": "v1",
            "activationNetMin": self.to_decimal(cfg.get("activationNetMin", base.get("activationNetMin"))),
            "discountTiers": tiers,
            "commissionByDepth": {
                "1": self.to_decimal(cbd.get("1", self.default_commission_by_depth[1])),
                "2": self.to_decimal(cbd.get("2", self.default_commission_by_depth[2])),
                "3": self.to_decimal(cbd.get("3", self.default_commission_by_depth[3])),
            },
            "payoutDay": self.to_decimal(cfg.get("payoutDay", base.get("payoutDay"))),
            "cutRule": str(cfg.get("cutRule") or base.get("cutRule") or "hard_cut_no_pass"),
        }

    def normalize_app_config(self, raw: Any) -> dict:
        merged = self.merge_dict(self.default_app_config(), raw if isinstance(raw, dict) else {})
        rewards = self.normalize_rewards_config(merged.get("rewards"))
        orders_raw = merged.get("orders") if isinstance(merged.get("orders"), dict) else {}
        pos_raw = merged.get("pos") if isinstance(merged.get("pos"), dict) else {}
        stocks_raw = merged.get("stocks") if isinstance(merged.get("stocks"), dict) else {}
        payments_raw = merged.get("payments") if isinstance(merged.get("payments"), dict) else {}
        ml_raw = payments_raw.get("mercadoLibre") if isinstance(payments_raw.get("mercadoLibre"), dict) else {}
        warnings_raw = merged.get("adminWarnings") if isinstance(merged.get("adminWarnings"), dict) else {}
        order_status_map = pos_raw.get("orderStatusByDeliveryStatus") if isinstance(pos_raw.get("orderStatusByDeliveryStatus"), dict) else {}

        return {
            "version": str(merged.get("version") or "app-v1"),
            "rewards": rewards,
            "orders": {
                "requireStockOnShipped": bool(orders_raw.get("requireStockOnShipped", True)),
                "requireDispatchLinesOnShipped": bool(orders_raw.get("requireDispatchLinesOnShipped", True)),
            },
            "pos": {
                "defaultCustomerName": str(pos_raw.get("defaultCustomerName") or "Publico en General"),
                "defaultPaymentStatus": str(pos_raw.get("defaultPaymentStatus") or "paid_branch"),
                "defaultDeliveryStatus": str(pos_raw.get("defaultDeliveryStatus") or "delivered_branch"),
                "orderStatusByDeliveryStatus": {
                    "delivered_branch": str(order_status_map.get("delivered_branch") or "delivered"),
                    "paid_branch": str(order_status_map.get("paid_branch") or "paid"),
                },
            },
            "stocks": {
                "requireLinkedUserForTransferReceive": bool(stocks_raw.get("requireLinkedUserForTransferReceive", True)),
            },
            "payments": {
                "mercadoLibre": {
                    "enabled": bool(ml_raw.get("enabled", False)),
                    "accessToken": str(ml_raw.get("accessToken") or ""),
                    "checkoutPreferencesUrl": str(ml_raw.get("checkoutPreferencesUrl") or "https://api.mercadopago.com/checkout/preferences"),
                    "paymentInfoUrlTemplate": str(ml_raw.get("paymentInfoUrlTemplate") or "https://api.mercadopago.com/v1/payments/{payment_id}"),
                    "notificationUrl": str(ml_raw.get("notificationUrl") or ""),
                    "successUrl": str(ml_raw.get("successUrl") or ""),
                    "failureUrl": str(ml_raw.get("failureUrl") or ""),
                    "pendingUrl": str(ml_raw.get("pendingUrl") or ""),
                    "currencyId": str(ml_raw.get("currencyId") or "MXN"),
                    "webhookSecret": str(ml_raw.get("webhookSecret") or ""),
                },
            },
            "adminWarnings": {
                "showCommissions": bool(warnings_raw.get("showCommissions", True)),
                "showShipping": bool(warnings_raw.get("showShipping", True)),
                "showPendingPayments": bool(warnings_raw.get("showPendingPayments", True)),
                "showPendingTransfers": bool(warnings_raw.get("showPendingTransfers", True)),
                "showPosSalesToday": bool(warnings_raw.get("showPosSalesToday", True)),
            },
        }

    def _load_app_config_cached_impl(self) -> dict:
        cfg = self.get_by_id("CONFIG", self.app_config_entity_id())
        if cfg and isinstance(cfg, dict):
            return self.normalize_app_config(cfg.get("config"))
        legacy_rewards_item = self.get_by_id("CONFIG", self.legacy_rewards_config_entity_id())
        if legacy_rewards_item and isinstance(legacy_rewards_item.get("config"), dict):
            base = self.default_app_config()
            base["rewards"] = legacy_rewards_item.get("config") or self.default_rewards_config()
            return self.normalize_app_config(base)
        return self.normalize_app_config(self.default_app_config())

    def load_app_config(self) -> dict:
        cfg = self._load_app_config_cached()
        if not self.get_by_id("CONFIG", self.app_config_entity_id()):
            now = self.now_iso()
            item = {
                "entityType": "config",
                "name": "app",
                "configId": self.app_config_entity_id(),
                "config": cfg,
                "createdAt": now,
                "updatedAt": now,
            }
            self.put_entity("CONFIG", self.app_config_entity_id(), item, created_at_iso=now)
        return cfg

    def save_legacy_rewards_config(self, cfg: dict) -> None:
        now = self.now_iso()
        existing = self.get_by_id("CONFIG", self.legacy_rewards_config_entity_id())
        normalized_rewards = self.normalize_rewards_config(cfg)
        if not existing:
            item = {
                "entityType": "config",
                "name": "rewards",
                "configId": self.legacy_rewards_config_entity_id(),
                "config": normalized_rewards,
                "createdAt": now,
                "updatedAt": now,
            }
            self.put_entity("CONFIG", self.legacy_rewards_config_entity_id(), item, created_at_iso=now)
            return

        self.update_by_id(
            "CONFIG",
            self.legacy_rewards_config_entity_id(),
            "SET #c = :c, updatedAt = :u",
            {":c": normalized_rewards, ":u": now},
            ean={"#c": "config"},
        )

    def save_app_config(self, cfg: dict) -> dict:
        now = self.now_iso()
        normalized = self.normalize_app_config(cfg)
        existing = self.get_by_id("CONFIG", self.app_config_entity_id())
        if not existing:
            item = {
                "entityType": "config",
                "name": "app",
                "configId": self.app_config_entity_id(),
                "config": normalized,
                "createdAt": now,
                "updatedAt": now,
            }
            self.put_entity("CONFIG", self.app_config_entity_id(), item, created_at_iso=now)
        else:
            self.update_by_id(
                "CONFIG",
                self.app_config_entity_id(),
                "SET #c = :c, updatedAt = :u",
                {":c": normalized, ":u": now},
                ean={"#c": "config"},
            )
        self.save_legacy_rewards_config(normalized.get("rewards") or self.default_rewards_config())
        self._load_app_config_cached.cache_clear()
        return normalized

    def load_rewards_config(self) -> dict:
        cfg = self.load_app_config()
        rewards = cfg.get("rewards") if isinstance(cfg, dict) else None
        return self.normalize_rewards_config(rewards)

    def save_rewards_config(self, cfg: dict) -> dict:
        app_cfg = self.load_app_config()
        app_cfg["rewards"] = self.normalize_rewards_config(cfg)
        saved = self.save_app_config(app_cfg)
        return saved.get("rewards") or self.default_rewards_config()

    def get_rewards_config_handler(self) -> dict:
        return self.json_response(200, {"config": self.load_rewards_config()})

    def put_rewards_config(self, payload: dict, headers: Optional[dict] = None) -> dict:
        if not isinstance(payload, dict) or not payload:
            return self.json_response(200, {"message": "config invalida", "Error": "BadRequest"})
        candidate = payload.get("config") if isinstance(payload.get("config"), dict) else payload
        cfg = self.normalize_rewards_config(candidate)
        saved = self.save_rewards_config(cfg)
        self.audit_event("config.rewards.update", headers, payload, {"scope": "rewards"})
        return self.json_response(200, {"config": saved})

    def get_app_config_handler(self) -> dict:
        return self.json_response(200, {"config": self.load_app_config()})

    def put_app_config(self, payload: dict, headers: Optional[dict] = None) -> dict:
        if not isinstance(payload, dict) or not payload:
            return self.json_response(200, {"message": "config invalida", "Error": "BadRequest"})
        current = self.load_app_config()
        incoming = payload.get("config") if isinstance(payload.get("config"), dict) else payload
        merged = self.merge_dict(current, incoming)
        saved = self.save_app_config(merged)
        self.audit_event("config.app.update", headers, payload, {"scope": "app"})
        return self.json_response(200, {"config": saved})
