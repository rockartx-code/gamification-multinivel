import boto3
import base64
import time
import core_utils as utils # Importado desde la Layer
import dashboard_common
from dashboard_common import (
    _active_notifications_for_customer,
    _build_goals,
    _build_month_node_index,
    _build_network_tree_with_month,
    _calc_vg_from_tree,
    _campaign_payload,
    _compute_buy_again_ids,
    _find_effective_sponsor,
    _get_month_state,
    _get_product_summary,
    _get_rank_dash,
    _is_product_active,
    _mxn_to_vp_dash,
    _network_members_from_tree,
    _notify_goal_achievements,
    _pick_product_image,
    _prev_month_key,
)

FRONTEND_URL = utils.os.getenv("FRONTEND_BASE_URL", "https://www.findingu.com.mx")
BUCKET_NAME = utils.os.getenv("BUCKET_NAME", "findingu-ventas")
_s3 = boto3.client('s3', region_name=utils.AWS_REGION)






# Clientes de AWS (Athena para análitica avanzada, opcional)
try:
    athena = boto3.client('athena')
    ATHENA_DB = utils.os.getenv("ATHENA_DATABASE", "findingu_analytics")
    ATHENA_OUTPUT = f"s3://{utils.BUCKET_NAME}/athena-results/"
    _ATHENA_ENABLED = True
except Exception:
    _ATHENA_ENABLED = False

# --- HELPERS DE FECHA ---


# --- HELPERS DE PRODUCTOS Y CAMPAÑAS ---





# --- HELPERS DE RED Y METAS ---









# --- VP / VG HELPERS (inline, sin importar commissions_lambda) ---



def _postorder_node_ids(nodes: dict, children_by_leader: dict) -> list:
    """Ids en orden post-orden (hijos antes que padres), iterativo y sin ciclos."""
    order = []
    visited = set()
    roots = [
        cid for cid, node in nodes.items()
        if not node.get("leaderId") or node["leaderId"] not in nodes
    ]
    stack = [(cid, False) for cid in roots]
    while stack:
        cid, expanded = stack.pop()
        if expanded:
            order.append(cid)
            continue
        if cid in visited:
            continue
        visited.add(cid)
        stack.append((cid, True))
        for child_id in children_by_leader.get(cid, []):
            if child_id in nodes and child_id not in visited:
                stack.append((child_id, False))

    # Nodos en un ciclo o con líder inexistente: no se alcanzan desde ninguna raíz.
    for cid in nodes:
        if cid not in visited:
            visited.add(cid)
            order.append(cid)
    return order


def _aggregate_vg_by_node(nodes: dict, children_by_leader: dict, vp_by_id: dict,
                          max_levels: int) -> dict:
    """VG de TODOS los nodos en una sola pasada, O(N × max_levels).

    Para cada nodo se guarda el VP acumulado por nivel de profundidad
    (`acc[d]` = VP de los descendientes a exactamente `d` niveles). En orden
    post-orden, el vector de un padre es el de sus hijos desplazado un nivel,
    así que el VG (suma del vector) sale sin recorrer la subred de cada nodo.
    """
    levels = {}
    for cid in _postorder_node_ids(nodes, children_by_leader):
        acc = [0.0] * (max_levels + 1)
        acc[0] = vp_by_id.get(cid, 0.0)
        for child_id in children_by_leader.get(cid, []):
            child_acc = levels.get(child_id)
            if not child_acc:
                continue
            for depth in range(1, max_levels + 1):
                acc[depth] += child_acc[depth - 1]
        levels[cid] = acc
    return {cid: sum(acc) for cid, acc in levels.items()}




def _count_direct_at_rank_dash(cid: str, month_key: str, customers_raw: list,
                                required_rank: str, mxn_per_vp: float, rank_thresholds: list) -> int:
    count = 0
    for c in customers_raw:
        if str(c.get("leaderId", "")) != str(cid):
            continue
        did = str(c.get("customerId", ""))
        # Build a small tree just for this direct to get their VG (up to 5 levels is expensive; use netVolume as proxy for simplicity)
        st = _get_month_state(did, month_key)
        direct_net = float(utils._to_decimal(st.get("netVolume", 0)))
        direct_vg = _mxn_to_vp_dash(direct_net, mxn_per_vp)
        if _get_rank_dash(direct_vg, rank_thresholds) == required_rank:
            count += 1
    return count





def _resolve_user_context(query: dict, headers: dict):
    """Devuelve (user_id, is_guest)."""
    user_id_raw = (query or {}).get("userId") or (headers or {}).get("x-user-id")
    if user_id_raw is not None:
        try:
            return int(user_id_raw), False
        except (ValueError, TypeError):
            return str(user_id_raw), False

    email_raw = (query or {}).get("email") or (headers or {}).get("x-user-email")
    if email_raw:
        email_norm = email_raw.strip().lower()
        auth = utils._get_by_id("AUTH", email_norm)
        if auth and auth.get("customerId") is not None:
            return auth.get("customerId"), False

    return None, True

# --- TAREA DE ORQUESTACIÓN: SYNC S3 TABLES ---

def handle_sync_iceberg(order_id):
    """
    Invocado por Step Functions.
    Crea un registro optimizado en S3 (Iceberg) para consultas SQL masivas.
    """
    order = utils._get_by_id("ORDER", order_id)
    if not order: return {"status": "NOT_FOUND"}

    # Aquí se enviaría el dato a un Glue DataBrew o se escribiría directamente
    # como Parquet en la ruta de S3 Tables. 
    # Por ahora, simulamos el éxito de la integración analítica.
    utils._log("analytics_sync_started", "INFO", orderId=order_id)
    return {"status": "SYNCED", "orderId": order_id}

# --- HELPERS DE ATHENA (REPORTES) ---

def _query_athena(sql):
    """Ejecuta SQL y retorna el primer registro (para KPIs)."""
    try:
        execution = athena.start_query_execution(
            QueryString=sql,
            QueryExecutionContext={'Database': ATHENA_DB},
            ResultConfiguration={'OutputLocation': ATHENA_OUTPUT}
        )
        query_id = execution['QueryExecutionId']
        
        # Espera simple (Máximo 5 segundos para mantener UX)
        for _ in range(5):
            state = athena.get_query_execution(QueryExecutionId=query_id)['QueryExecution']['Status']['State']
            if state == 'SUCCEEDED': break
            if state in ['FAILED', 'CANCELLED']: return None
            time.sleep(1)
        
        results = athena.get_query_results(QueryExecutionId=query_id)
        rows = results['ResultSet']['Rows']
        if len(rows) < 2: return {}
        
        headers = [c['VarCharValue'] for c in rows[0]['Data']]
        values = [c.get('VarCharValue', '0') for c in rows[1]['Data']]
        return dict(zip(headers, values))
    except Exception as e:
        utils._log_error("athena_query_failed", e)
        return None

# --- HANDLERS ADMIN (GRANULARES) ---

def get_admin_stats():
    """GET /admin/stats - Usa S3 Tables (Athena)"""
    month = utils._month_key()
    sql = f"""
        SELECT sum(netTotal) as total_sales, count(*) as order_count 
        FROM orders_iceberg WHERE monthKey = '{month}'
    """
    stats = _query_athena(sql)
    return utils._json_response(200, {"stats": stats or {"total_sales": 0, "order_count": 0}})

def get_admin_orders(query):
    """GET /admin/orders?status=X&limit=N - Órdenes filtradas por status"""
    limit = int(query.get("limit", 50))
    status_filter = (query.get("status") or "").lower().strip()
    items = utils._query_bucket("ORDER", forward=False)
    if status_filter:
        items = [o for o in items if (o.get("status") or "").lower() == status_filter]
    total = len(items)
    items = items[:limit]
    return utils._json_response(200, {"orders": items, "total": total, "limit": limit})

def get_admin_warnings():
    """GET /admin/warnings - Alertas reales desde DynamoDB"""
    cfg = utils._load_app_config()
    warning_cfg = cfg.get("adminWarnings") if isinstance(cfg.get("adminWarnings"), dict) else {}

    orders = utils._query_bucket("ORDER")
    now_date = utils._now_iso()[:10]

    paid_no_ship = sum(1 for o in orders if (o.get("status") or "").lower() == "paid")
    pending_pay = sum(1 for o in orders if (o.get("status") or "").lower() == "pending")

    # Comisiones pendientes de depositar (status CONFIRMED, sin recibo).
    # Esta query leía UNA sola página: con más de 1 MB de meses contables el
    # aviso salía corto y se dejaban de pagar comisiones sin ninguna señal.
    from boto3.dynamodb.conditions import Key as _Key
    try:
        comm_items = utils._query_all_pages(
            KeyConditionExpression=_Key("PK").eq("COMMISSION_MONTH")
        )
    except Exception:
        comm_items = []
    commissions_count = sum(
        1 for item in comm_items
        if utils._to_decimal(item.get("totalConfirmed")) > 0 and (item.get("status") or "") != "PAID"
    )

    # Transferencias pendientes
    transfers = utils._query_bucket("STOCK_TRANSFER")
    pending_transfers = sum(1 for t in transfers if (t.get("status") or "").lower() == "pending")

    # Ventas POS de hoy
    pos_sales_today = sum(
        1 for s in utils._query_bucket("POS_SALE", sk_prefix=now_date)
        if str(s.get("createdAt") or "")[:10] == now_date
    )

    warnings = []
    if warning_cfg.get("showCommissions", True) and commissions_count:
        warnings.append({"type": "commissions", "text": f"{commissions_count} comisiones pendientes por depositar", "severity": "high"})
    if warning_cfg.get("showShipping", True) and paid_no_ship:
        warnings.append({"type": "shipping", "text": f"{paid_no_ship} pedidos pagados sin envío", "severity": "medium"})
    if warning_cfg.get("showPendingPayments", True) and pending_pay:
        warnings.append({"type": "payments", "text": f"{pending_pay} pedidos pendientes de pago", "severity": "low"})
    if warning_cfg.get("showPendingTransfers", True) and pending_transfers:
        warnings.append({"type": "stocks", "text": f"{pending_transfers} transferencias pendientes por recibir", "severity": "medium"})
    if warning_cfg.get("showPosSalesToday", True) and pos_sales_today:
        warnings.append({"type": "pos", "text": f"{pos_sales_today} ventas POS registradas hoy", "severity": "low"})

    return utils._json_response(200, {"warnings": warnings})

# --- HANDLERS USUARIO (GRANULARES) ---







def get_user_performance(user_id):
    """GET /user/performance - Metas y Volumen"""
    mxn_per_vp    = utils._mxn_per_vp()
    activation_vp = utils._activation_vp()

    month_key = utils._month_key()
    state     = utils._get_by_id("ASSOCIATE_MONTH", f"{user_id}#{month_key}")
    net_vol   = utils._to_decimal(state.get("netVolume") if state else 0)
    vp        = _mxn_to_vp_dash(float(net_vol), mxn_per_vp)

    return utils._json_response(200, {
        "monthKey": month_key,
        "netVolume": float(net_vol),
        "vp": round(vp, 2),
        "isActive": vp >= activation_vp,
        "activationVp": activation_vp,
    })

def get_user_commissions(user_id):
    """GET /user/commissions - Saldo actual"""
    month_key = utils._month_key()
    comm_item = utils._table.get_item(
        Key={"PK": utils.COMMISSION_MONTH_PK, "SK": utils._ledger_sk(user_id, month_key)}
    ).get("Item", {})

    return utils._json_response(200, {
        "pending": float(utils._to_decimal(comm_item.get("totalPending", 0))),
        "confirmed": float(utils._to_decimal(comm_item.get("totalConfirmed", 0))),
        "blocked": float(utils._to_decimal(comm_item.get("totalBlocked", 0)))
    })

# --- HANDLERS USUARIO COMPLETOS ---

def _catalog_section(products_raw: list) -> tuple:
    """Productos visibles en tienda, destacados y producto del mes."""
    products, featured = [], []
    for item in products_raw:
        if not _is_product_active(item) or not bool(item.get("inOnlineStore", True)):
            continue
        resumen = _get_product_summary(item)
        products.append({
            clave: resumen[clave] for clave in (
                "id", "name", "price", "badge", "img", "description",
                "copyFacebook", "copyInstagram", "copyWhatsapp",
                "variants", "categoryIds", "tags",
                "inOnlineStore", "inPOS", "commissionable",
            )
        })
        if len(featured) < 4:
            imagenes = item.get("images") or []
            featured.append({
                "id": resumen["id"],
                "label": resumen["name"],
                "hook": resumen.get("hook") or "",
                "story": _pick_product_image(imagenes, ["redes"]) or resumen["img"],
                "feed": _pick_product_image(imagenes, ["miniatura", "redes"]) or resumen["img"],
                "banner": _pick_product_image(imagenes, ["landing"]) or resumen["img"],
            })

    product_of_month = None
    pom_item = utils._get_by_id("PRODUCT_OF_MONTH", "current")
    if pom_item:
        producto = utils._get_by_id("PRODUCT", int(pom_item.get("productId")))
        if _is_product_active(producto):
            product_of_month = _get_product_summary(producto)

    return products, featured, product_of_month


def _active_categories() -> list:
    """Categorías activas, ordenadas para el catálogo."""
    return [
        {
            "id": str(c.get("categoryId") or c.get("id") or ""),
            "name": str(c.get("name") or ""),
            "parentId": c.get("parentId"),
            "position": int(c.get("position") or 0),
            "active": True,
        }
        for c in utils._query_bucket("PRODUCT_CATEGORY")
        if bool(c.get("active", True))
    ]


def _associate_section(customer: dict, cfg: dict, bonus_cfg: dict, products_raw: list,
                       month_key: str, prev_month_key: str) -> dict:
    """Metas, red, métricas y comisiones de un socio autenticado."""
    max_levels = utils._max_network_levels()
    # Solo el socio y su descendencia (árbol persistido + BatchGetItem), en vez
    # de leer la colección CUSTOMER completa.
    customers_raw, _scope = utils._load_network_scope(customer, max_depth=max_levels)
    month_states = utils._load_month_states(
        [c.get("customerId") for c in customers_raw], month_key
    )
    tree = _build_network_tree_with_month(
        str(customer.get("customerId")), month_key, customers_raw, cfg,
        max_depth=max_levels, month_states=month_states,
    )

    goals = _build_goals(customer, tree, customers_raw, cfg,
                         bonus_cfg=bonus_cfg, month_states=month_states)
    network = _network_members_from_tree(tree, max_rows=30)
    buy_again_ids = _compute_buy_again_ids(customer, products_raw)

    cid = str(customer.get("customerId", ""))
    mxn_per_vp = utils._mxn_per_vp()
    my_net = float(utils._to_decimal(
        _get_month_state(cid, month_key, month_states).get("netVolume", 0)
    ))
    vp_val = _mxn_to_vp_dash(my_net, mxn_per_vp)
    vg_val = _calc_vg_from_tree(tree, mxn_per_vp)

    # Correo por metas recién logradas (transición False → True).
    _notify_goal_achievements(customer, goals, bonus_cfg)
    dashboard_common.persist_dashboard_cache(customer, goals, network, buy_again_ids)

    return {
        "goals": goals,
        "network": network,
        "buyAgainIds": buy_again_ids,
        "notifications": _active_notifications_for_customer(customer.get("customerId")),
        "vp": vp_val,
        "vg": vg_val,
        "rank": _get_rank_dash(vg_val, bonus_cfg.get("rankThresholds") or [], vp=vp_val),
        "bonuses": dashboard_common.load_bonus_awards(cid, month_key),
        "commissions": dashboard_common.build_commission_summary(
            customer, month_key, prev_month_key,
            payout_day=int(utils._to_decimal(cfg.get("payoutDay", 10))),
        ),
    }


def get_user_dashboard(query: dict, headers: dict) -> dict:
    """GET /user-dashboard — dashboard completo del socio o invitado (legacy).

    Endpoint heredado: el frontend usa `GET /catalog` + `GET /customers/dashboard`.
    Se conserva por compatibilidad y comparte con ellos toda la lógica a través
    de `dashboard_common`.
    """
    user_id, is_guest = _resolve_user_context(query, headers)
    customer = utils._get_by_id("CUSTOMER", int(user_id)) if user_id is not None else None

    products_raw = utils._query_bucket("PRODUCT")
    products, featured, product_of_month = _catalog_section(products_raw)
    campaigns = [
        _campaign_payload(c) for c in utils._query_bucket("CAMPAIGN")
        if bool(c.get("active", True))
    ]

    app_cfg = utils._load_app_config()
    cfg = app_cfg.get("rewards") or {}
    bonus_cfg = app_cfg.get("bonuses") or {}

    es_socio = bool(customer) and isinstance(customer, dict)
    if es_socio:
        seccion = _associate_section(
            customer, cfg, bonus_cfg, products_raw,
            utils._month_key(), _prev_month_key(),
        )
        discount_rate = utils._to_decimal(customer.get("discountRate"))
        user_payload = {
            "discountPercent": int((discount_rate * 100).quantize(utils.D_ONE)) if discount_rate else 0,
            "discountActive": bool(customer.get("activeBuyer") or discount_rate > 0),
        }
    else:
        seccion = {
            "goals": [], "network": [], "notifications": [], "bonuses": [],
            "buyAgainIds": [str(p["id"]) for p in products[:3]],
            "vp": 0.0, "vg": 0.0, "rank": "", "commissions": None,
        }
        user_payload = None

    respuesta = utils._json_response(200, {
        "isGuest": bool(is_guest),
        "settings": {
            "cutoffDay": 25, "cutoffHour": 23, "cutoffMinute": 59,
            "userCode": "" if is_guest else str(user_id), "networkGoal": 300,
        },
        "user": user_payload,
        "sponsor": _find_effective_sponsor(customer),
        "goals": seccion["goals"],
        "products": products,
        "featured": featured,
        "productOfMonth": product_of_month,
        "campaigns": campaigns,
        "categories": _active_categories(),
        "notifications": seccion["notifications"],
        "networkMembers": seccion["network"],
        "buyAgainIds": seccion["buyAgainIds"],
        "commissions": seccion["commissions"],
        "vp": round(seccion["vp"], 2),
        "vg": round(seccion["vg"], 2),
        "rank": seccion["rank"],
        "bonuses": seccion["bonuses"],
    })
    # RFC 8594: avisa a cualquier cliente que siga usando el endpoint.
    respuesta["headers"].update({
        "Deprecation": "true",
        "Link": '</catalog>; rel="successor-version", </customers/dashboard>; rel="successor-version"',
        "Warning": '299 - "Endpoint obsoleto: use GET /catalog y GET /customers/dashboard"',
    })
    return respuesta



# --- HONOR BOARD ---

def get_honor_board() -> dict:
    """
    GET /honor-board — Top 10 por VG y Top 10 por VP del mes actual + mes anterior para delta.
    Complejidad O(N_customers) por mes; adecuado para redes de hasta ~5 000 socios.
    """
    app_cfg    = utils._load_app_config()
    bonus_cfg  = app_cfg.get("bonuses") or {}
    mxn_per_vp = utils._mxn_per_vp()
    rank_thresh = bonus_cfg.get("rankThresholds") or []

    month_key  = utils._month_key()
    prev_mk    = _prev_month_key()

    customers_raw = utils._query_bucket("CUSTOMER")
    cfg_rewards = app_cfg.get("rewards") or {}
    max_levels = utils._max_network_levels()

    def _compute_ranking(mk: str):
        """Devuelve [{customerId, name, vp, vg, rank}] para el mes `mk`.

        Antes construía el árbol COMPLETO del sistema una vez por cada cliente
        (y cada construcción hacía un GetItem por cliente): 3N² operaciones,
        ~1.9 M con 800 clientes, muy por encima del timeout de Lambda.

        Ahora los estados del mes se cargan en un solo bloque y el VG de todos
        los clientes sale de un único recorrido post-orden del bosque: cada
        nodo acumula su VP y el de sus descendientes hasta `max_levels`.
        """
        month_states = utils._load_month_states(
            [c.get("customerId") for c in customers_raw if isinstance(c, dict)], mk
        )
        nodes, children_by_leader = _build_month_node_index(mk, customers_raw, cfg_rewards, month_states)

        # VP por nodo con la MISMA regla que el panel del cliente y el motor de
        # comisiones: puntos del catálogo (monthVP) si existen; si no, pesos ÷ tarifa.
        # Antes usaba solo pesos ÷ tarifa y el Cuadro de Honor decía "19" para
        # quien su panel marcaba 20 VP.
        vp_by_id = {
            cid: float(node["monthVP"]) if node.get("monthVP") is not None
            else _mxn_to_vp_dash(node["monthSpend"], mxn_per_vp)
            for cid, node in nodes.items()
        }

        vg_by_id = _aggregate_vg_by_node(nodes, children_by_leader, vp_by_id, max_levels)

        entries = []
        for cid, node in nodes.items():
            vg = vg_by_id.get(cid, 0.0)
            entries.append({
                "customerId": cid,
                "name": node.get("name") or "",
                "vp": round(vp_by_id.get(cid, 0.0), 2),
                "vg": round(vg, 2),
                "rank": _get_rank_dash(vg, rank_thresh),
            })
        return entries

    # Cálculo mes actual
    current = _compute_ranking(month_key)

    # Top 10 por VG
    by_vg_sorted = sorted(current, key=lambda e: e["vg"], reverse=True)[:10]
    # Top 10 por VP
    by_vp_sorted = sorted(current, key=lambda e: e["vp"], reverse=True)[:10]

    # Posición anterior para delta (mes previo)
    prev = _compute_ranking(prev_mk)
    prev_vg_pos = {e["customerId"]: i + 1 for i, e in enumerate(sorted(prev, key=lambda e: e["vg"], reverse=True)[:10])}
    prev_vp_pos = {e["customerId"]: i + 1 for i, e in enumerate(sorted(prev, key=lambda e: e["vp"], reverse=True)[:10])}

    def _enrich(entries, prev_pos_map):
        result = []
        for i, e in enumerate(entries):
            entry = {**e, "position": i + 1}
            prev_pos = prev_pos_map.get(e["customerId"])
            if prev_pos is not None:
                entry["prevPosition"] = prev_pos
            result.append(entry)
        return result

    return utils._json_response(200, {
        "monthKey": month_key,
        "byVg": _enrich(by_vg_sorted, prev_vg_pos),
        "byVp": _enrich(by_vp_sorted, prev_vp_pos),
    })


def _normalize_campaign(item: dict) -> dict:
    """Normalize a campaign item: ensure 'id' is present."""
    cid = item.get("campaignId") or item.get("id") or ""
    return {**item, "id": cid}

def _handle_campaign_asset(method, body, headers):
    """POST /dashboard/campaigns/assets — sube un asset de campana a S3."""
    err = utils._require_admin(headers, "access_screen_stocks")
    if err:
        return err
    if method != "POST":
        return utils._json_response(405, {"message": "Método no permitido"})
    name = body.get("name", "upload")
    b64_data = body.get("contentBase64")
    content_type = body.get("contentType", "image/png")
    if not b64_data:
        return utils._json_response(400, {"message": "contentBase64 requerido"})
    try:
        raw_data = base64.b64decode(b64_data)
        asset_id = f"assets/{utils.uuid.uuid4()}-{name}"
        _s3.put_object(
            Bucket=BUCKET_NAME,
            Key=asset_id,
            Body=raw_data,
            ContentType=content_type,
            ACL='public-read'
        )
        url = f"https://{BUCKET_NAME}.s3.{utils.AWS_REGION}.amazonaws.com/{asset_id}"
    except Exception as e:
        print(f"[S3_CAMPAIGN_ASSET_ERROR] {e}")
        return utils._json_response(500, {"message": "Error al subir a S3"})
    asset_item = {
        "entityType": "asset", "assetId": asset_id, "name": name,
        "url": url, "contentType": content_type, "createdAt": utils._now_iso()
    }
    utils._put_entity("ASSET", asset_id, asset_item)
    return utils._json_response(201, {"asset": asset_item})


def _handle_campaigns(method, body):
    """GET /campaigns  |  POST /campaigns — también resuelve /dashboard/campaigns"""
    if method == "GET":
        items = utils._query_bucket("CAMPAIGN")
        return utils._json_response(200, {"campaigns": [_normalize_campaign(c) for c in items]})
    if method == "POST":
        cid = body.get("id") or f"CMP-{utils.uuid.uuid4().hex[:8].upper()}"
        now = utils._now_iso()
        existing = utils._get_by_id("CAMPAIGN", cid) if body.get("id") else None
        campaign = {
            "entityType": "campaign", "campaignId": cid, "id": cid,
            "name": body.get("name"), "active": bool(body.get("active", True)),
            "type": body.get("type") or "multinivel",
            "hook": body.get("hook") or "",
            "description": body.get("description") or "",
            "banner": body.get("banner"), "story": body.get("story"), "feed": body.get("feed"),
            "heroImage": body.get("heroImage"),
            "heroBadge": body.get("heroBadge"),
            "heroTitle": body.get("heroTitle"),
            "heroAccent": body.get("heroAccent"),
            "heroTail": body.get("heroTail"),
            "heroDescription": body.get("heroDescription"),
            "ctaPrimaryText": body.get("ctaPrimaryText"),
            "ctaSecondaryText": body.get("ctaSecondaryText"),
            "benefits": body.get("benefits") or [],
            "updatedAt": now,
        }
        saved = utils._put_entity("CAMPAIGN", cid, campaign, created_at_iso=existing.get("createdAt") if existing else None)
        return utils._json_response(201, {"campaign": _normalize_campaign(saved)})
    return utils._json_response(405, {"message": "Método no permitido"})


def _handle_notifications(method, body, segments):
    """GET /notifications  |  POST /notifications  |  POST /notifications/{id}/read
    También resuelve /dashboard/notifications/* tras strip del prefijo."""
    if method == "GET":
        items = utils._query_bucket("NOTIFICATION")
        return utils._json_response(200, {"notifications": items})
    if method == "POST":
        if len(segments) == 3 and segments[2] == "read":
            ntf_id = segments[1]
            user_id = body.get("userId") or body.get("customerId")
            pk = f"NOTIFICATION_READ#{user_id}"
            utils._table.put_item(Item={
                "PK": pk, "SK": ntf_id, "readAt": utils._now_iso(), "entityType": "notificationRead"
            })
            return utils._json_response(200, {"ok": True})
        nid = body.get("id") or f"NTF-{utils.uuid.uuid4().hex[:8].upper()}"
        ntf = {
            "entityType": "notification", "notificationId": nid,
            "title": body.get("title"), "description": body.get("description"),
            "linkUrl": body.get("linkUrl"), "startAt": body.get("startAt"),
            "endAt": body.get("endAt"), "active": True, "createdAt": utils._now_iso()
        }
        saved = utils._put_entity("NOTIFICATION", nid, ntf)
        return utils._json_response(201, {"notification": saved})
    return utils._json_response(405, {"message": "Método no permitido"})


# --- LAMBDA HANDLER PRINCIPAL ---

def lambda_handler(event, context):
    # 1. Detectar invocación de Step Functions (Sync Analítico)
    if event.get("task") == "sync_iceberg":
        return handle_sync_iceberg(event.get("orderId"))

    # 2. Peticiones de API Gateway
    if (event.get("httpMethod") or "").upper() == "OPTIONS":
        return utils._cors_preflight_response()
    # API Gateway entrega /dashboard/{proxy+}: se quita el prefijo del recurso.
    request = utils._http_request(event, strip_prefix="dashboard")
    method = request.method
    body, query, headers = request.body, request.query, request.headers
    segments = request.segments

    try:
        root = segments[0] if segments else ""

        # ── /admin/*  (también resuelve /dashboard/admin/* tras strip del prefijo) ─
        if root == "admin":
            err = utils._require_admin(headers, "access_screen_stats")
            if err: return err
            sub = segments[1] if len(segments) > 1 else ""
            if sub == "stats": return get_admin_stats()
            if sub == "orders": return get_admin_orders(query)
            if sub == "warnings": return get_admin_warnings()

        # ── /user/* ─────────────────────────────────────────────────────────────
        if root == "user":
            uid = headers.get("x-user-id") or query.get("userId")
            if not uid: return utils._json_response(400, {"message": "userId missing"})
            err = utils._require_self_or_admin(headers, uid)
            if err: return err
            sub = segments[1] if len(segments) > 1 else ""
            if sub == "performance": return get_user_performance(uid)
            if sub == "commissions": return get_user_commissions(uid)

        # ── /user-dashboard  ────────────────────────────────────────────────────
        if root == "user-dashboard":
            uid = headers.get("x-user-id") or query.get("userId")
            err = utils._require_self_or_admin(headers, uid)
            if err: return err
            return get_user_dashboard(query, headers)

        # ── /honor-board  (también /dashboard/honor-board) ──────────────────────
        if root == "honor-board" and method == "GET":
            return get_honor_board()

        # ── /campaigns  (también /dashboard/campaigns) ───────────────────────────
        if root == "campaigns":
            if len(segments) > 1 and segments[1] == "assets":
                return _handle_campaign_asset(method, body, headers)
            if method == "POST":
                err = utils._require_admin(headers, "access_screen_stocks")
                if err: return err
            return _handle_campaigns(method, body)

        # ── /notifications  (también /dashboard/notifications) ───────────────────
        if root == "notifications":
            if method == "POST" and not (len(segments) == 3 and segments[2] == "read"):
                err = utils._require_admin(headers, "config_manage")
                if err: return err
            return _handle_notifications(method, body, segments)

        return utils._json_response(404, {"message": "Dashboard endpoint not found"})

    except Exception as e:
        utils._log_error("dashboard_unhandled_error", e)
        return utils._json_response(500, {"message": "Error cargando datos", "error": str(e)})
