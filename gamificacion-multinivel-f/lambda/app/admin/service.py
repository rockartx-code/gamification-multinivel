from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Callable, Dict, List, Tuple


_ALL_PRIVILEGES = [
    "view_orders", "create_orders", "update_orders", "delete_orders",
    "view_customers", "create_customers", "update_customers", "delete_customers",
    "view_products", "create_products", "update_products", "delete_products",
    "view_stocks", "create_stocks", "update_stocks", "delete_stocks",
    "view_rewards", "update_rewards",
    "view_reports", "export_data",
    "view_audit",
]
def _normalize_privileges(raw: Any) -> dict:
    data = raw if isinstance(raw, dict) else {}
    return {priv: bool(data.get(priv)) for priv in _ALL_PRIVILEGES}


def _to_float(value: Any) -> float:
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _to_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


class AdminDashboardService:
    def __init__(
        self,
        *,
        load_app_config: Callable[[], dict],
    ) -> None:
        self.load_app_config = load_app_config

    def build_admin_warnings(
        self,
        paid_count: int,
        pending_count: int,
        commissions_count: int,
        pending_transfers_count: int = 0,
        pos_sales_today_count: int = 0,
    ) -> List[dict]:
        app_cfg = self.load_app_config()
        raw_warning_cfg = app_cfg.get("adminWarnings") if isinstance(app_cfg, dict) else None
        warning_cfg: Dict[str, Any] = raw_warning_cfg if isinstance(raw_warning_cfg, dict) else {}
        warnings: List[dict] = []
        show_commissions = bool(warning_cfg.get("showCommissions", True))
        show_shipping = bool(warning_cfg.get("showShipping", True))
        show_pending_payments = bool(warning_cfg.get("showPendingPayments", True))
        show_pending_transfers = bool(warning_cfg.get("showPendingTransfers", True))
        show_pos_sales_today = bool(warning_cfg.get("showPosSalesToday", True))
        if show_commissions and commissions_count:
            warnings.append({"type": "commissions", "text": f"{commissions_count} comisiones pendientes por depositar", "severity": "high"})
        if show_shipping and paid_count:
            warnings.append({"type": "shipping", "text": f"{paid_count} pedidos pagados sin envio", "severity": "medium"})
        if show_pending_payments and pending_count:
            warnings.append({"type": "payments", "text": f"{pending_count} pedidos pendientes de pago", "severity": "low"})
        if show_pending_transfers and pending_transfers_count:
            warnings.append({"type": "stocks", "text": f"{pending_transfers_count} transferencias pendientes por recibir", "severity": "medium"})
        if show_pos_sales_today and pos_sales_today_count:
            warnings.append({"type": "pos", "text": f"{pos_sales_today_count} ventas POS registradas hoy", "severity": "low"})
        return warnings

    def count_pending_transfers(self, transfers_raw: List[dict]) -> int:
        pending_transfers_count = 0
        for transfer in transfers_raw:
            if (transfer.get("status") or "").strip().lower() == "pending":
                pending_transfers_count += 1
        return pending_transfers_count

    def count_today_pos_sales(self, pos_sales_raw: List[dict], now_dt: datetime | None = None) -> int:
        today_prefix = (now_dt or datetime.now(timezone.utc)).strftime("%Y-%m-%d")
        pos_sales_today_count = 0
        for sale in pos_sales_raw:
            created_at = str(sale.get("createdAt") or "")
            if created_at.startswith(today_prefix):
                pos_sales_today_count += 1
        return pos_sales_today_count

    def dashboard_alerts_payload(
        self,
        *,
        paid_count: int,
        pending_count: int,
        commissions_count: int,
        transfers_raw: List[dict],
        pos_sales_raw: List[dict],
    ) -> Dict[str, Any]:
        pending_transfers_count = self.count_pending_transfers(transfers_raw)
        pos_sales_today_count = self.count_today_pos_sales(pos_sales_raw)
        warnings = self.build_admin_warnings(
            paid_count,
            pending_count,
            commissions_count,
            pending_transfers_count,
            pos_sales_today_count,
        )
        return {
            "warnings": warnings,
            "pendingTransfersCount": pending_transfers_count,
            "posSalesTodayCount": pos_sales_today_count,
        }

    def transform_customers_for_admin(
        self,
        customers_raw: List[dict],
        commission_month_by_customer_month: Dict[str, dict],
        receipt_by_customer_month: Dict[str, str],
        prev_month_key: str,
        current_month_key: str,
        commissions_by_id: Dict[str, float],
    ) -> Tuple[List[dict], Dict[str, int], int, float]:
        customers: List[dict] = []
        customers_by_level: Dict[str, int] = {}
        commissions_count = 0
        commissions_total = 0.0

        for item in customers_raw:
            comm = _to_float(item.get("commissions") or 0)
            cid = item.get("customerId")
            current_comm_key = f"{cid}#{current_month_key}" if cid is not None else ""
            prev_comm_key = f"{cid}#{prev_month_key}" if cid is not None else ""

            comm_item = commission_month_by_customer_month.get(current_comm_key)
            current_pending = _to_float(comm_item.get("totalPending")) if comm_item else 0.0
            current_confirmed = _to_float(comm_item.get("totalConfirmed")) if comm_item else 0.0

            prev_comm_item = commission_month_by_customer_month.get(prev_comm_key)
            prev_confirmed = _to_float(prev_comm_item.get("totalConfirmed")) if prev_comm_item else 0.0

            receipt_key = f"{cid}#{prev_month_key}" if cid is not None else ""
            prev_receipt_url = receipt_by_customer_month.get(receipt_key, "")

            if prev_confirmed <= 0:
                prev_status = "no_moves"
            elif prev_receipt_url:
                prev_status = "paid"
            else:
                prev_status = "pending"

            clabe_interbancaria = (item.get("clabeInterbancaria") or item.get("clabe") or "").strip()
            customers.append({
                "id": item.get("customerId"),
                "name": item.get("name"),
                "email": item.get("email"),
                "leaderId": item.get("leaderId"),
                "level": item.get("level"),
                "discount": item.get("discount"),
                "canAccessAdmin": bool(item.get("canAccessAdmin")),
                "privileges": _normalize_privileges(item.get("privileges")),
                "commissions": comm,
                "commissionsPrevMonthKey": prev_month_key,
                "commissionsPrevMonth": prev_confirmed,
                "commissionsCurrentPending": current_pending,
                "commissionsCurrentConfirmed": current_confirmed,
                "commissionsPrevStatus": prev_status,
                "commissionsPrevReceiptUrl": prev_receipt_url,
                "clabeInterbancaria": clabe_interbancaria,
            })
            level = item.get("level") or "Sin nivel"
            customers_by_level[level] = customers_by_level.get(level, 0) + 1
            if comm > 0:
                commissions_count += 1
                commissions_total += comm

        return customers, customers_by_level, commissions_count, commissions_total

    def transform_orders_for_admin(
        self,
        orders_raw: List[dict],
    ) -> Tuple[Dict[str, int], float, List[dict]]:
        status_counts = {"pending": 0, "paid": 0, "delivered": 0, "shipped": 0, "canceled": 0, "refunded": 0}
        sales_total = 0.0
        orders: List[dict] = []

        for item in orders_raw:
            st = (item.get("status") or "").lower()
            if st in status_counts:
                status_counts[st] += 1
            tot = _to_float(item.get("netTotal") or item.get("total") or 0)
            sales_total += tot
            orders.append({
                "id": item.get("orderId"),
                "createdAt": item.get("createdAt"),
                "customer": item.get("customerName"),
                "total": tot,
                "status": item.get("status"),
                "items": item.get("items") or [],
                "stockId": item.get("stockId"),
                "attendantUserId": item.get("attendantUserId"),
                "paymentStatus": item.get("paymentStatus"),
                "deliveryStatus": item.get("deliveryStatus"),
                "shippingType": item.get("shippingType"),
                "trackingNumber": item.get("trackingNumber"),
                "deliveryPlace": item.get("deliveryPlace"),
                "deliveryDate": item.get("deliveryDate"),
            })

        return status_counts, sales_total, orders

    def transform_products_for_admin(
        self,
        products_raw: List[dict],
    ) -> Tuple[int, List[dict]]:
        active_products = 0
        products: List[dict] = []
        for item in products_raw:
            if item.get("active"):
                active_products += 1
            products.append({
                "id": _to_int(item.get("productId")),
                "name": item.get("name"),
                "price": _to_float(item.get("price") or 0),
                "active": bool(item.get("active")),
                "sku": item.get("sku"),
                "hook": item.get("hook"),
                "description": item.get("description"),
                "copyFacebook": item.get("copyFacebook"),
                "copyInstagram": item.get("copyInstagram"),
                "copyWhatsapp": item.get("copyWhatsapp"),
                "tags": item.get("tags"),
                "images": item.get("images"),
            })
        return active_products, products

    def aggregate_kpis(
        self,
        customers: List[dict],
        orders: List[dict],
        active_products: int,
        commissions_total: float,
        sales_total: float,
    ) -> Dict[str, Any]:
        average_ticket = sales_total / len(orders) if orders else 0.0
        return {
            "salesTotal": sales_total,
            "averageTicket": average_ticket,
            "activeProducts": active_products,
            "customersTotal": len(customers),
            "commissionsTotalPending": commissions_total,
        }


__all__ = ["AdminDashboardService"]
