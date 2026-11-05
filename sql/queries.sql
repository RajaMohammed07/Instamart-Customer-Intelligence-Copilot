-- Q1: customers with large completed spend over 8,000
SELECT customer_id
FROM orders
WHERE status = 'completed' AND order_amount > 500
GROUP BY customer_id
HAVING SUM(order_amount) > 8000;

-- Q2: city and category revenue
SELECT c.city, o.category, SUM(o.order_amount) AS revenue, COUNT(*) AS orders
FROM (
    SELECT ord.order_id, ord.customer_id, ord.order_amount, ord.status, p.category
    FROM orders ord
    JOIN products p ON p.product_id = ord.product_id
) o
JOIN customers c ON c.customer_id = o.customer_id
WHERE o.status = 'completed'
GROUP BY c.city, o.category;

-- Q3: products above average catalogue price
SELECT product_id, category, price_inr
FROM products
WHERE price_inr > (SELECT AVG(price_inr) FROM products);

-- Q4: customers without completed order
SELECT c.customer_id
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id AND o.status = 'completed'
GROUP BY c.customer_id
HAVING COUNT(o.order_id) = 0;

-- Q5: customer spend above average
WITH customer_spend AS (
    SELECT customer_id, SUM(order_amount) AS total_spend
    FROM orders
    WHERE status = 'completed'
    GROUP BY customer_id
),
avg_spend AS (
    SELECT AVG(total_spend) AS avg_total FROM customer_spend
)
SELECT cs.customer_id, cs.total_spend
FROM customer_spend cs
CROSS JOIN avg_spend a
WHERE cs.total_spend > a.avg_total;

-- Q6: rank by city spend
WITH city_spend AS (
    SELECT c.city, o.customer_id, SUM(o.order_amount) AS total_spend
    FROM orders o
    JOIN customers c ON c.customer_id = o.customer_id
    WHERE o.status = 'completed'
    GROUP BY c.city, o.customer_id
)
SELECT city, customer_id, total_spend,
       RANK() OVER (PARTITION BY city ORDER BY total_spend DESC) AS rn_rank,
       DENSE_RANK() OVER (PARTITION BY city ORDER BY total_spend DESC) AS rn_dense,
       ROW_NUMBER() OVER (PARTITION BY city ORDER BY total_spend DESC) AS rn_row
FROM city_spend;

-- Q7: daily cumulative revenue
WITH daily AS (
    SELECT DATE(order_ts) AS day, SUM(order_amount) AS revenue
    FROM orders
    WHERE status = 'completed'
    GROUP BY DATE(order_ts)
)
SELECT day, revenue,
       SUM(revenue) OVER (ORDER BY day) AS cumulative_revenue
FROM daily;
