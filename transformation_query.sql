SELECT
c.customer_id,
c.customer_name,
c.email,
COUNT(o.order_id) AS total_orders,
COUNT(CASE WHEN o.order_status IN ('Shipped', 'Processing') THEN 1 END) AS active_orders,
COUNT(CASE WHEN o.order_status = 'Completed' THEN 1 END) AS completed_orders,
COUNT(CASE WHEN o.order_status = 'Cancelled' THEN 1 END) AS cancelled_orders,
COALESCE(SUM(o.total_amount), 0) AS total_amount_spent,
MIN(o.order_date) AS first_order_date,
MAX(o.order_date) AS last_order_date,
c.loyalty_level,
c.country
FROM mg_poc_catalog.upstream.customers c
LEFT JOIN mg_poc_catalog.upstream.orders o
ON c.customer_id = o.customer_id
GROUP BY
c.customer_id, c.customer_name, c.email, c.loyalty_level, c.country;