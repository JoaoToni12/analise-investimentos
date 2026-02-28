"""Quick validation script to test the full engine pipeline with real portfolio data."""

import sys

sys.path.insert(0, ".")

from engine.grey_zones import classify_all
from engine.models import Asset, AssetClass
from engine.portfolio import compute_class_weights, compute_portfolio_value, enrich_weights
from engine.rebalancer import compute_class_targets, compute_rebalancing
from ingestion.portfolio_loader import load_portfolio, load_portfolio_meta

positions = load_portfolio()
meta = load_portfolio_meta()
print(f"Positions: {len(positions)}")
print(f"Meta: {meta}")

assets = []
for p in positions:
    price = float(p.get("current_price", 0)) or float(p.get("avg_price", 0))
    assets.append(
        Asset(
            ticker=p["ticker"],
            asset_class=AssetClass.from_str(p.get("asset_class", "ACAO")),
            quantity=float(p["quantity"]),
            avg_price=float(p["avg_price"]),
            current_price=price,
            target_weight=float(p["target_weight_pct"]),
        )
    )

assets = enrich_weights(assets)
total = compute_portfolio_value(assets)
print(f"Total value: R$ {total:,.2f}")

class_w = compute_class_weights(assets)
class_t = compute_class_targets(assets)
print(f"Class weights: { {k.value: round(v, 1) for k, v in class_w.items()} }")
print(f"Class targets: { {k.value: round(v, 1) for k, v in class_t.items()} }")

zones = classify_all(assets, 0.20, 1.5)
statuses: dict[str, list[str]] = {}
for t, (s, b) in zones.items():
    statuses.setdefault(s.value, []).append(t)
for s, tickers in statuses.items():
    print(f"{s}: {len(tickers)} ativos -> {tickers[:5]}")

orders, residual = compute_rebalancing(assets, 1000, zones)
print(f"\nOrders: {len(orders)}, Residual: R$ {residual:.2f}")
for o in orders[:8]:
    print(f"  {o.action.value} {o.quantity}x {o.ticker} @ R${o.price:.2f} = R${o.amount:.2f}")

print("\nPipeline OK!")
