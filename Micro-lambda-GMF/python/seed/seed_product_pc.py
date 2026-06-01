"""
Seed de PC oficiales (Plan abril 2026 §1) en los productos de DynamoDB.

Empareja cada producto de la tabla (bucket PRODUCT) con la tabla oficial de
`product_pc_seed.json` por nombre normalizado (sin acentos, minúsculas, sin
paréntesis) o por alias, y actualiza `vpPoints` (y opcionalmente `price`).

Uso (desde Micro-lambda-GMF/python, con la Layer/core_utils importable y credenciales AWS):

    python seed/seed_product_pc.py            # dry-run: solo muestra qué cambiaría
    python seed/seed_product_pc.py --apply     # aplica vpPoints
    python seed/seed_product_pc.py --apply --price   # también corrige el precio

Idempotente: si el producto ya tiene el vpPoints correcto, no lo reescribe.
"""
import argparse
import json
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import core_utils as utils  # noqa: E402


def _norm(text: str) -> str:
    text = str(text or "").lower().strip()
    text = "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")
    text = re.sub(r"\([^)]*\)", " ", text)      # quita paréntesis
    text = re.sub(r"[^a-z0-9]+", " ", text)      # solo alfanumérico
    return re.sub(r"\s+", " ", text).strip()


def _load_seed() -> list:
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "product_pc_seed.json")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)["products"]


def _match(seed_entry: dict, product_name_norm: str) -> bool:
    candidates = [seed_entry["name"]] + list(seed_entry.get("aliases", []))
    for cand in candidates:
        cn = _norm(cand)
        if cn and (cn in product_name_norm or product_name_norm in cn):
            return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Aplica los cambios (por defecto: dry-run).")
    parser.add_argument("--price", action="store_true", help="También corrige el precio según el plan.")
    args = parser.parse_args()

    seed = _load_seed()
    products = utils._query_bucket("PRODUCT")
    print(f"Productos en tabla: {len(products)} · entradas de seed: {len(seed)}")

    matched, changed, unmatched = 0, 0, []
    used_seed = set()

    for prod in products:
        pname = _norm(prod.get("name"))
        entry = next((s for s in seed if _match(s, pname)), None)
        if not entry:
            unmatched.append(prod.get("name"))
            continue
        matched += 1
        used_seed.add(entry["name"])

        target_pc = utils._to_decimal(entry["vpPoints"])
        current_pc = prod.get("vpPoints")
        needs_pc = current_pc is None or utils._to_decimal(current_pc) != target_pc

        updates = {}
        if needs_pc:
            updates["vpPoints"] = target_pc
        if args.price:
            target_price = utils._to_decimal(entry["price"])
            if utils._to_decimal(prod.get("price", 0)) != target_price:
                updates["price"] = target_price

        if not updates:
            continue
        changed += 1
        print(f"  {prod.get('name')!r}: {updates}")
        if args.apply:
            item = dict(prod)
            item.update(updates)
            item["updatedAt"] = utils._now_iso()
            pid = prod.get("productId") or prod.get("id")
            utils._put_entity("PRODUCT", pid, item, created_at_iso=prod.get("createdAt"))

    print(f"\nCoincidencias: {matched} · con cambios: {changed} · {'APLICADO' if args.apply else 'DRY-RUN'}")
    if unmatched:
        print(f"Sin coincidencia ({len(unmatched)}): {unmatched}")
    missing = [s['name'] for s in seed if s['name'] not in used_seed]
    if missing:
        print(f"Entradas de seed sin producto en tabla: {missing}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
