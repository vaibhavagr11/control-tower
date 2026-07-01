from control_tower.tools.oms import (
    lookup_order,
    lookup_orders_by_customer,
    cancel_order,
    create_replacement_order,
)
from control_tower.tools.carrier import (
    get_tracking_status,
    generate_return_label,
)
from control_tower.tools.payment import process_refund

ALL_TOOLS = [
    lookup_order,
    lookup_orders_by_customer,
    cancel_order,
    create_replacement_order,
    get_tracking_status,
    generate_return_label,
    process_refund,
]