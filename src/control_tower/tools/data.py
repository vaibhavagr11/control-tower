# ─── Customers ────────────────────────────────────────────────────────────────

CUSTOMERS = {
    "C-100": {
        "name": "Dana Lee",
        "email": "dana.lee@email.com",
        "phone": "+1-415-555-0192",
        "member_since": "2022-09-14",
        "shipping_addresses": [
            {"label": "home", "city": "San Francisco", "state": "CA", "zip": "94102"}
        ],
        "return_history": [],
        "order_history": ["ORD-5001", "ORD-5003", "ORD-5004", "ORD-5005"],
    },
    "C-200": {
        "name": "Sam Cruz",
        "email": "sam.cruz@email.com",
        "phone": "+1-512-555-0847",
        "member_since": "2026-06-09",
        "shipping_addresses": [
            {"label": "home", "city": "Austin", "state": "TX", "zip": "78701"}
        ],
        "return_history": [
            {"order_id": "ORD-4901", "reason": "wrong_item",       "refund_usd": 34.90, "date": "2026-05-10"},
            {"order_id": "ORD-4867", "reason": "not_as_described", "refund_usd": 59.90, "date": "2026-05-28"},
            {"order_id": "ORD-4923", "reason": "wrong_item",       "refund_usd": 29.90, "date": "2026-06-01"},
            {"order_id": "ORD-4988", "reason": "not_as_described", "refund_usd": 89.90, "date": "2026-06-18"},
        ],
        "order_history": ["ORD-4867", "ORD-4901", "ORD-4923", "ORD-4988", "ORD-5002"],
    },
    "C-300": {
        "name": "Priya Nair",
        "email": "priya.nair@email.com",
        "phone": "+1-206-555-0334",
        "member_since": "2024-12-03",
        "shipping_addresses": [
            {"label": "home", "city": "Seattle", "state": "WA", "zip": "98101"},
            {"label": "work", "city": "Bellevue", "state": "WA", "zip": "98004"},
        ],
        "return_history": [
            {"order_id": "ORD-4750", "reason": "wrong_size", "refund_usd": 49.90, "date": "2025-03-22"},
        ],
        "order_history": ["ORD-4750", "ORD-5006", "ORD-5007"],
    },
}

# ─── Orders ───────────────────────────────────────────────────────────────────
# Each order has a list of items — closer to how a real OMS stores orders.
# value_usd is the order total (sum of qty * unit_price across all items).

ORDERS = {
    "ORD-5001": {
        "customer_id": "C-100",
        "items": [
            {"name": "Ultra Stretch Jeans",        "sku": "APPRL-JN-032-BLK-32", "size": "32",  "color": "black", "qty": 1, "unit_price_usd": 49.90},
            {"name": "Heattech Crewneck T-Shirt",  "sku": "APPRL-TS-021-WHT-M",  "size": "M",   "color": "white", "qty": 2, "unit_price_usd": 19.90},
            {"name": "Merino Wool Cardigan",        "sku": "APPRL-CD-008-GRY-M",  "size": "M",   "color": "grey",  "qty": 1, "unit_price_usd": 89.90},
        ],
        "value_usd": 179.60,
        "status": "delivered",
        "tracking_number": "1Z999AA10123456781",
        "carrier": "UPS",
        "days_since_order": 6,
    },
    "ORD-5002": {
        "customer_id": "C-200",
        "items": [
            {"name": "Cashmere Turtleneck",         "sku": "APPRL-TN-055-CAM-L",  "size": "L",   "color": "camel", "qty": 1, "unit_price_usd": 129.90},
            {"name": "Cashmere Turtleneck",         "sku": "APPRL-TN-055-NVY-L",  "size": "L",   "color": "navy",  "qty": 1, "unit_price_usd": 129.90},
            {"name": "Puffer Jacket",               "sku": "APPRL-JK-009-BLK-L",  "size": "L",   "color": "black", "qty": 1, "unit_price_usd": 149.90},
        ],
        "value_usd": 409.70,
        "status": "delivered",
        "tracking_number": "1Z999AA10123456782",
        "carrier": "FedEx",
        "days_since_order": 2,
    },
    "ORD-5003": {
        "customer_id": "C-100",
        "items": [
            {"name": "Merino Wool Sweater",         "sku": "APPRL-SW-017-NVY-M",  "size": "M",   "color": "navy",  "qty": 1, "unit_price_usd": 79.90},
            {"name": "Wide Leg Chino Pants",        "sku": "APPRL-PT-041-BGE-M",  "size": "M",   "color": "beige", "qty": 1, "unit_price_usd": 49.90},
            {"name": "Airism Cotton T-Shirt",       "sku": "APPRL-TS-033-WHT-M",  "size": "M",   "color": "white", "qty": 3, "unit_price_usd": 14.90},
        ],
        "value_usd": 174.50,
        "status": "in_transit",
        "tracking_number": "1Z999AA10123456783",
        "carrier": "UPS",
        "days_since_order": 9,
    },
    "ORD-5004": {
        "customer_id": "C-100",
        "items": [
            {"name": "Linen Relaxed Shirt",         "sku": "APPRL-SH-062-BLU-S",  "size": "S",   "color": "blue",  "qty": 1, "unit_price_usd": 39.90},
            {"name": "Linen Shorts",                "sku": "APPRL-ST-019-OLV-S",  "size": "S",   "color": "olive", "qty": 1, "unit_price_usd": 29.90},
            {"name": "Airism Cotton T-Shirt",       "sku": "APPRL-TS-033-WHT-S",  "size": "S",   "color": "white", "qty": 2, "unit_price_usd": 14.90},
        ],
        "value_usd": 99.60,
        "status": "delivered",
        "tracking_number": "1Z999AA10123456784",
        "carrier": "FedEx",
        "days_since_order": 3,
    },
    "ORD-5005": {
        "customer_id": "C-100",
        "items": [
            {"name": "Fleece Full-Zip Jacket",      "sku": "APPRL-JK-022-GRY-M",  "size": "M",   "color": "grey",  "qty": 1, "unit_price_usd": 59.90},
            {"name": "Ribbed Beanie",               "sku": "APPRL-AC-005-BLK-OS", "size": "OS",  "color": "black", "qty": 1, "unit_price_usd": 14.90},
        ],
        "value_usd": 74.80,
        "status": "out_for_delivery",
        "tracking_number": "1Z999AA10123456785",
        "carrier": "UPS",
        "days_since_order": 1,
    },
    "ORD-5006": {
        "customer_id": "C-300",
        "items": [
            {"name": "Puffer Jacket",               "sku": "APPRL-JK-009-OLV-L",  "size": "L",   "color": "olive", "qty": 1, "unit_price_usd": 149.90},
            {"name": "Heattech Extra Warm Leggings","sku": "APPRL-LG-011-BLK-M",  "size": "M",   "color": "black", "qty": 2, "unit_price_usd": 24.90},
            {"name": "Ribbed Beanie",               "sku": "APPRL-AC-005-NVY-OS", "size": "OS",  "color": "navy",  "qty": 1, "unit_price_usd": 14.90},
        ],
        "value_usd": 214.60,
        "status": "in_transit",
        "tracking_number": "1Z999AA10123456786",
        "carrier": "USPS",
        "days_since_order": 5,
    },
    "ORD-5007": {
        "customer_id": "C-300",
        "items": [
            {"name": "Heattech Turtleneck",         "sku": "APPRL-TN-044-WHT-S",  "size": "S",   "color": "white", "qty": 1, "unit_price_usd": 29.90},
            {"name": "Heattech Turtleneck",         "sku": "APPRL-TN-044-BLK-S",  "size": "S",   "color": "black", "qty": 1, "unit_price_usd": 29.90},
        ],
        "value_usd": 59.80,
        "status": "cancelled",
        "tracking_number": None,
        "carrier": None,
        "days_since_order": 1,
    },
}

# ─── Carrier tracking events ───────────────────────────────────────────────────

TRACKING_EVENTS = {
    "1Z999AA10123456781": {
        "status": "delivered",
        "location": "San Francisco, CA",
        "timestamp": "2026-06-24 14:32",
        "events": [
            {"time": "2026-06-24 14:32", "desc": "Delivered — left at front door"},
            {"time": "2026-06-24 08:10", "desc": "Out for delivery"},
            {"time": "2026-06-23 22:45", "desc": "Arrived at local facility"},
        ],
        "estimated_delivery": None,
        "delay_reason": None,
    },
    "1Z999AA10123456782": {
        "status": "delivered",
        "location": "Austin, TX",
        "timestamp": "2026-06-28 11:05",
        "events": [
            {"time": "2026-06-28 11:05", "desc": "Delivered — signature obtained"},
            {"time": "2026-06-28 09:00", "desc": "Out for delivery"},
        ],
        "estimated_delivery": None,
        "delay_reason": None,
    },
    "1Z999AA10123456783": {
        "status": "delayed",
        "location": "Chicago, IL — sorting hub",
        "timestamp": "2026-06-27 03:18",
        "events": [
            {"time": "2026-06-27 03:18", "desc": "Package held at sorting facility"},
            {"time": "2026-06-25 18:00", "desc": "Departed origin facility"},
            {"time": "2026-06-25 14:00", "desc": "Picked up"},
        ],
        "estimated_delivery": "2026-07-02",
        "delay_reason": "weather_disruption",
    },
    "1Z999AA10123456784": {
        "status": "delivered",
        "location": "San Francisco, CA",
        "timestamp": "2026-06-27 13:55",
        "events": [
            {"time": "2026-06-27 13:55", "desc": "Delivered — left at front door"},
            {"time": "2026-06-27 09:30", "desc": "Out for delivery"},
        ],
        "estimated_delivery": None,
        "delay_reason": None,
    },
    "1Z999AA10123456785": {
        "status": "out_for_delivery",
        "location": "San Francisco, CA",
        "timestamp": "2026-06-30 09:15",
        "events": [
            {"time": "2026-06-30 09:15", "desc": "Out for delivery"},
            {"time": "2026-06-29 23:00", "desc": "Arrived at local facility"},
        ],
        "estimated_delivery": "2026-06-30",
        "delay_reason": None,
    },
    "1Z999AA10123456786": {
        "status": "in_transit",
        "location": "Denver, CO",
        "timestamp": "2026-06-29 16:40",
        "events": [
            {"time": "2026-06-29 16:40", "desc": "In transit to next facility"},
            {"time": "2026-06-28 08:00", "desc": "Departed origin facility"},
        ],
        "estimated_delivery": "2026-07-01",
        "delay_reason": None,
    },
}

# ─── Transaction logs (mutated at runtime by tool calls) ──────────────────────

REFUND_LOG: dict[str, dict] = {}
