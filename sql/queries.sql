-- Q1: WHERE and HAVING. Qualifying completed-order amount is summed per customer.
SELECT customer_id, SUM(order_amount) AS qualifying_spend
FROM orders
WHERE status = 'completed' AND order_amount > 500
GROUP BY customer_id
HAVING SUM(order_amount) > 8000
ORDER BY qualifying_spend DESC;

-- Q2: completed revenue by customer city and product category.
SELECT c.city, p.category, SUM(o.order_amount) AS revenue, COUNT(*) AS order_count
FROM orders AS o
JOIN customers AS c ON c.customer_id = o.customer_id
JOIN products AS p ON p.product_id = o.product_id
WHERE o.status = 'completed'
GROUP BY c.city, p.category
ORDER BY c.city, p.category;

-- Q3: products priced above the average catalogue price.
SELECT product_id, product_name, category, price_inr
FROM products
WHERE price_inr > (SELECT AVG(price_inr) FROM products)
ORDER BY price_inr DESC;

-- Q4: customers without any completed order.
SELECT c.customer_id
FROM customers AS c
LEFT JOIN orders AS o
    ON o.customer_id = c.customer_id
    AND o.status = 'completed'
WHERE o.order_id IS NULL
ORDER BY c.customer_id;

-- Q5: two CTEs calculate each customer's completed spend and its average.
WITH customer_spend AS (
    SELECT customer_id, SUM(order_amount) AS total_spend
    FROM orders
    WHERE status = 'completed'
    GROUP BY customer_id
),
average_spend AS (
    SELECT AVG(total_spend) AS mean_customer_spend
    FROM customer_spend
)
SELECT cs.customer_id, cs.total_spend, av.mean_customer_spend
FROM customer_spend AS cs
CROSS JOIN average_spend AS av
WHERE cs.total_spend > av.mean_customer_spend
ORDER BY cs.total_spend DESC;

-- Q6: customer completed spend ranks within each city.
WITH customer_city_spend AS (
    SELECT c.city, c.customer_id, SUM(o.order_amount) AS total_spend
    FROM customers AS c
    JOIN orders AS o ON o.customer_id = c.customer_id
    WHERE o.status = 'completed'
    GROUP BY c.city, c.customer_id
)
SELECT city,
       customer_id,
       total_spend,
       RANK() OVER (PARTITION BY city ORDER BY total_spend DESC) AS spend_rank,
       DENSE_RANK() OVER (PARTITION BY city ORDER BY total_spend DESC) AS dense_spend_rank,
       ROW_NUMBER() OVER (
           PARTITION BY city
           ORDER BY total_spend DESC, customer_id
       ) AS spend_row_number
FROM customer_city_spend
ORDER BY city, spend_rank, customer_id;

-- Q7: daily completed revenue and its running cumulative total.
WITH daily_revenue AS (
    SELECT DATE(order_ts) AS day, SUM(order_amount) AS revenue
    FROM orders
    WHERE status = 'completed'
    GROUP BY DATE(order_ts)
)
SELECT day,
       revenue,
       SUM(revenue) OVER (ORDER BY day) AS cumulative_revenue
FROM daily_revenue
ORDER BY day;
