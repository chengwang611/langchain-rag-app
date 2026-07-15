-- ============================================================================
-- Data Engineer Interview SQL Practice — 40 Queries
-- ============================================================================
-- Schema: employees, departments, sales, orders, customers, products
-- Each query includes sample data, the query, and expected result.
-- ============================================================================

-- ============================================================================
-- SAMPLE DATA SETUP (run once to create tables)
-- ============================================================================

-- DROP TABLE IF EXISTS employees, departments, sales, orders, customers, products;

CREATE TABLE departments (
    dept_id   INT PRIMARY KEY,
    dept_name VARCHAR(50) NOT NULL
);

CREATE TABLE employees (
    emp_id    INT PRIMARY KEY,
    emp_name  VARCHAR(100) NOT NULL,
    dept_id   INT REFERENCES departments(dept_id),
    salary    DECIMAL(10,2) NOT NULL,
    hire_date DATE NOT NULL,
    manager_id INT  -- self-referencing FK
);

CREATE TABLE customers (
    cust_id   INT PRIMARY KEY,
    cust_name VARCHAR(100) NOT NULL,
    city      VARCHAR(50),
    signup_date DATE NOT NULL
);

CREATE TABLE products (
    prod_id   INT PRIMARY KEY,
    prod_name VARCHAR(100) NOT NULL,
    category  VARCHAR(50),
    price     DECIMAL(10,2) NOT NULL
);

CREATE TABLE orders (
    order_id   INT PRIMARY KEY,
    cust_id    INT REFERENCES customers(cust_id),
    order_date DATE NOT NULL,
    total_amount DECIMAL(12,2) NOT NULL
);

CREATE TABLE order_items (
    order_id INT REFERENCES orders(order_id),
    prod_id  INT REFERENCES products(prod_id),
    quantity INT NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    PRIMARY KEY (order_id, prod_id)
);

-- ============================================================================
-- INSERT SAMPLE DATA
-- ============================================================================

INSERT INTO departments VALUES
(1, 'Engineering'),
(2, 'Data'),
(3, 'Product'),
(4, 'Marketing'),
(5, 'Finance');

INSERT INTO employees VALUES
(1,  'Alice',   1, 120000, '2019-03-15', NULL),
(2,  'Bob',     1, 110000, '2020-01-10', 1),
(3,  'Charlie', 2, 130000, '2018-07-22', NULL),
(4,  'Diana',   2, 125000, '2019-11-01', 3),
(5,  'Eve',     3, 105000, '2021-06-15', NULL),
(6,  'Frank',   1, 115000, '2020-09-01', 1),
(7,  'Grace',   4,  95000, '2022-02-14', NULL),
(8,  'Hank',    2, 140000, '2017-05-30', 3),
(9,  'Ivy',     5, 135000, '2019-08-20', NULL),
(10, 'Jack',    3, 100000, '2021-12-01', 5),
(11, 'Karen',   1, 118000, '2020-04-18', 1),
(12, 'Leo',     4,  92000, '2022-08-10', 7);

INSERT INTO customers VALUES
(1, 'Acme Corp',      'New York',   '2020-01-15'),
(2, 'Globex Inc',     'Chicago',    '2020-03-22'),
(3, 'Initech',        'Austin',     '2020-06-10'),
(4, 'Umbrella Corp',  'New York',   '2021-01-05'),
(5, 'Stark Industries','Los Angeles','2021-04-18'),
(6, 'Wayne Enterprises','Chicago',  '2021-07-30'),
(7, 'Oscorp',         'New York',   '2022-02-14'),
(8, 'LexCorp',        'Austin',     '2022-05-20');

INSERT INTO products VALUES
(1, 'Widget A',    'Widgets',  19.99),
(2, 'Widget B',    'Widgets',  24.99),
(3, 'Gadget X',    'Gadgets',  49.99),
(4, 'Gadget Y',    'Gadgets',  79.99),
(5, 'Service Pro', 'Services', 199.99),
(6, 'Service Lite','Services',  99.99);

INSERT INTO orders VALUES
(1, 1, '2022-01-10', 149.95),
(2, 1, '2022-02-15', 249.90),
(3, 2, '2022-01-20',  99.98),
(4, 3, '2022-03-05', 399.96),
(5, 1, '2022-04-10',  79.99),
(6, 4, '2022-04-12', 199.99),
(7, 5, '2022-05-01', 499.95),
(8, 2, '2022-06-15', 149.97),
(9, 6, '2022-07-20',  59.98),
(10,3, '2022-08-01', 299.97),
(11,1, '2022-09-10', 124.95),
(12,7, '2022-10-05', 399.96);

INSERT INTO order_items VALUES
(1, 1, 5, 19.99),
(1, 3, 1, 49.99),
(2, 2, 10, 24.99),
(3, 1, 5, 19.99),
(4, 4, 5, 79.99),
(5, 4, 1, 79.99),
(6, 5, 1, 199.99),
(7, 3, 10, 49.99),
(8, 1, 3, 19.99),
(8, 2, 3, 24.99),
(9, 6, 1, 59.98),
(10,4, 3, 79.99),
(10,3, 1, 49.99),
(11,1, 2, 19.99),
(11,2, 2, 24.99),
(11,3, 1, 49.99),
(12,4, 5, 79.99);


-- ============================================================================
-- QUERY 1: SELECT with WHERE and ORDER BY
-- Task: Find all employees in Engineering (dept_id=1) earning > $110,000,
--        ordered by salary descending.
-- ============================================================================

SELECT emp_name, salary, hire_date
FROM employees
WHERE dept_id = 1
  AND salary > 110000
ORDER BY salary DESC;

-- Expected result:
--  emp_name | salary  | hire_date
-- ----------+---------+-----------
--  Alice    | 120000  | 2019-03-15
--  Karen    | 118000  | 2020-04-18
--  Frank    | 115000  | 2020-09-01


-- ============================================================================
-- QUERY 2: INNER JOIN
-- Task: List every employee with their department name.
-- ============================================================================

SELECT e.emp_name, d.dept_name, e.salary
FROM employees e
JOIN departments d ON e.dept_id = d.dept_id
ORDER BY d.dept_name, e.salary DESC;

-- Expected result (first 5 rows):
--  emp_name | dept_name   | salary
-- ----------+-------------+--------
--  Hank     | Data        | 140000
--  Charlie  | Data        | 130000
--  Diana    | Data        | 125000
--  Alice    | Engineering | 120000
--  Karen    | Engineering | 118000


-- ============================================================================
-- QUERY 3: LEFT JOIN
-- Task: Show all departments and the count of employees in each,
--        including departments with zero employees.
-- ============================================================================

SELECT d.dept_name, COUNT(e.emp_id) AS employee_count
FROM departments d
LEFT JOIN employees e ON d.dept_id = e.dept_id
GROUP BY d.dept_name
ORDER BY employee_count DESC;

-- Expected result:
--  dept_name   | employee_count
-- -------------+---------------
--  Engineering | 4
--  Data        | 3
--  Product     | 2
--  Marketing   | 2
--  Finance     | 1


-- ============================================================================
-- QUERY 4: GROUP BY with HAVING
-- Task: Find departments with an average salary above $115,000.
-- ============================================================================

SELECT d.dept_name, ROUND(AVG(e.salary), 2) AS avg_salary
FROM employees e
JOIN departments d ON e.dept_id = d.dept_id
GROUP BY d.dept_name
HAVING AVG(e.salary) > 115000
ORDER BY avg_salary DESC;

-- Expected result:
--  dept_name   | avg_salary
-- -------------+-----------
--  Data        | 131666.67
--  Finance     | 135000.00
--  Engineering | 115750.00


-- ============================================================================
-- QUERY 5: Window Function — ROW_NUMBER()
-- Task: Rank employees within each department by salary (highest = 1).
-- ============================================================================

SELECT emp_name, dept_id, salary,
       ROW_NUMBER() OVER (PARTITION BY dept_id ORDER BY salary DESC) AS rank_in_dept
FROM employees
ORDER BY dept_id, rank_in_dept;

-- Expected result (first 6 rows):
--  emp_name | dept_id | salary  | rank_in_dept
-- ----------+---------+---------+-------------
--  Alice    | 1       | 120000  | 1
--  Karen    | 1       | 118000  | 2
--  Frank    | 1       | 115000  | 3
--  Bob      | 1       | 110000  | 4
--  Hank     | 2       | 140000  | 1
--  Charlie  | 2       | 130000  | 2


-- ============================================================================
-- QUERY 6: Window Function — RANK() vs DENSE_RANK()
-- Task: Show the difference between RANK and DENSE_RANK when salaries tie.
-- ============================================================================

SELECT emp_name, dept_id, salary,
       RANK()       OVER (PARTITION BY dept_id ORDER BY salary DESC) AS rank_,
       DENSE_RANK() OVER (PARTITION BY dept_id ORDER BY salary DESC) AS dense_rank_
FROM employees
ORDER BY dept_id, salary DESC;

-- Expected result for dept_id=1 (no ties in current data, so rank_ = dense_rank_):
--  emp_name | dept_id | salary  | rank_ | dense_rank_
-- ----------+---------+---------+-------+------------
--  Alice    | 1       | 120000  | 1     | 1
--  Karen    | 1       | 118000  | 2     | 2
--  Frank    | 1       | 115000  | 3     | 3
--  Bob      | 1       | 110000  | 4     | 4


-- ============================================================================
-- QUERY 7: Window Function — LAG() / LEAD()
-- Task: For each employee, show the previous hire date in the same department.
-- ============================================================================

SELECT emp_name, dept_id, hire_date,
       LAG(hire_date) OVER (PARTITION BY dept_id ORDER BY hire_date) AS prev_hire_date
FROM employees
ORDER BY dept_id, hire_date;

-- Expected result for dept_id=1:
--  emp_name | dept_id | hire_date  | prev_hire_date
-- ----------+---------+------------+---------------
--  Alice    | 1       | 2019-03-15 | NULL
--  Bob      | 1       | 2020-01-10 | 2019-03-15
--  Karen    | 1       | 2020-04-18 | 2020-01-10
--  Frank    | 1       | 2020-09-01 | 2020-04-18


-- ============================================================================
-- QUERY 8: Running Total with SUM() OVER()
-- Task: Calculate a running total of salaries ordered by hire date.
-- ============================================================================

SELECT emp_name, hire_date, salary,
       SUM(salary) OVER (ORDER BY hire_date) AS running_total_salary
FROM employees
ORDER BY hire_date;

-- Expected result (first 5 rows):
--  emp_name | hire_date  | salary  | running_total_salary
-- ----------+------------+---------+---------------------
--  Hank     | 2017-05-30 | 140000  | 140000
--  Charlie  | 2018-07-22 | 130000  | 270000
--  Alice    | 2019-03-15 | 120000  | 390000
--  Ivy      | 2019-08-20 | 135000  | 525000
--  Diana    | 2019-11-01 | 125000  | 650000


-- ============================================================================
-- QUERY 9: Common Table Expression (CTE)
-- Task: Find employees who earn more than their department's average salary.
-- ============================================================================

WITH dept_avg AS (
    SELECT dept_id, AVG(salary) AS avg_salary
    FROM employees
    GROUP BY dept_id
)
SELECT e.emp_name, e.salary, d.dept_name, ROUND(da.avg_salary, 2) AS dept_avg_salary
FROM employees e
JOIN dept_avg da ON e.dept_id = da.dept_id
JOIN departments d ON e.dept_id = d.dept_id
WHERE e.salary > da.avg_salary
ORDER BY d.dept_name, e.salary DESC;

-- Expected result:
--  emp_name | salary  | dept_name   | dept_avg_salary
-- ----------+---------+-------------+----------------
--  Hank     | 140000  | Data        | 131666.67
--  Alice    | 120000  | Engineering | 115750.00
--  Karen    | 118000  | Engineering | 115750.00
--  Eve      | 105000  | Product     | 102500.00
--  Grace    |  95000  | Marketing   |  93500.00


-- ============================================================================
-- QUERY 10: Self-Join (Manager/Employee hierarchy)
-- Task: List each employee with their manager's name.
-- ============================================================================

SELECT e.emp_name AS employee,
       COALESCE(m.emp_name, 'No Manager') AS manager,
       e.salary
FROM employees e
LEFT JOIN employees m ON e.manager_id = m.emp_id
ORDER BY manager, e.salary DESC;

-- Expected result:
--  employee | manager    | salary
-- ----------+------------+--------
--  Alice    | No Manager | 120000
--  Charlie  | No Manager | 130000
--  Eve      | No Manager | 105000
--  Grace    | No Manager |  95000
--  Ivy      | No Manager | 135000
--  Karen    | Alice      | 118000
--  Frank    | Alice      | 115000
--  Bob      | Alice      | 110000
--  Hank     | Charlie    | 140000
--  Diana    | Charlie    | 125000
--  Jack     | Eve        | 100000
--  Leo      | Grace      |  92000


-- ============================================================================
-- QUERY 11: Subquery in WHERE
-- Task: Find employees who earn more than the highest-paid Marketing employee.
-- ============================================================================

SELECT emp_name, salary, dept_id
FROM employees
WHERE salary > (
    SELECT MAX(salary)
    FROM employees
    WHERE dept_id = 4  -- Marketing
)
ORDER BY salary DESC;

-- Expected result:
--  emp_name | salary  | dept_id
-- ----------+---------+--------
--  Hank     | 140000  | 2
--  Ivy      | 135000  | 5
--  Charlie  | 130000  | 2
--  Diana    | 125000  | 2
--  Alice    | 120000  | 1
--  Karen    | 118000  | 1
--  Frank    | 115000  | 1
--  Bob      | 110000  | 1
--  Eve      | 105000  | 3
--  Jack     | 100000  | 3


-- ============================================================================
-- QUERY 12: Correlated Subquery
-- Task: Find employees whose salary is above the average of their own department.
-- ============================================================================

SELECT e.emp_name, e.salary, e.dept_id
FROM employees e
WHERE e.salary > (
    SELECT AVG(e2.salary)
    FROM employees e2
    WHERE e2.dept_id = e.dept_id
)
ORDER BY e.dept_id, e.salary DESC;

-- Expected result:
--  emp_name | salary  | dept_id
-- ----------+---------+--------
--  Alice    | 120000  | 1
--  Karen    | 118000  | 1
--  Hank     | 140000  | 2
--  Eve      | 105000  | 3
--  Grace    |  95000  | 4


-- ============================================================================
-- QUERY 13: CASE WHEN (Conditional Logic)
-- Task: Categorize employees into salary bands.
-- ============================================================================

SELECT emp_name, salary,
       CASE
           WHEN salary >= 130000 THEN 'Executive'
           WHEN salary >= 115000 THEN 'Senior'
           WHEN salary >= 100000 THEN 'Mid'
           ELSE 'Junior'
       END AS salary_band
FROM employees
ORDER BY salary DESC;

-- Expected result (first 5 rows):
--  emp_name | salary  | salary_band
-- ----------+---------+------------
--  Hank     | 140000  | Executive
--  Ivy      | 135000  | Executive
--  Charlie  | 130000  | Executive
--  Diana    | 125000  | Senior
--  Alice    | 120000  | Senior


-- ============================================================================
-- QUERY 14: UNION / UNION ALL
-- Task: Create a combined list of all people and companies (employees + customers).
-- ============================================================================

SELECT emp_name AS name, 'Employee' AS type FROM employees
UNION ALL
SELECT cust_name AS name, 'Customer' AS type FROM customers
ORDER BY type, name;

-- Expected result (first 5 rows):
--  name               | type
-- --------------------+---------
--  Acme Corp          | Customer
--  Globex Inc         | Customer
--  Initech            | Customer
--  LexCorp            | Customer
--  Oscorp             | Customer


-- ============================================================================
-- QUERY 15: EXISTS
-- Task: Find customers who have placed at least one order.
-- ============================================================================

SELECT c.cust_name, c.city
FROM customers c
WHERE EXISTS (
    SELECT 1
    FROM orders o
    WHERE o.cust_id = c.cust_id
)
ORDER BY c.cust_name;

-- Expected result:
--  cust_name        | city
-- ------------------+-------------
--  Acme Corp        | New York
--  Globex Inc       | Chicago
--  Initech          | Austin
--  Oscorp           | New York
--  Stark Industries | Los Angeles
--  Umbrella Corp    | New York
--  Wayne Enterprises| Chicago


-- ============================================================================
-- QUERY 16: NOT EXISTS (Anti-Join)
-- Task: Find customers who have NEVER placed an order.
-- ============================================================================

SELECT c.cust_name, c.city
FROM customers c
WHERE NOT EXISTS (
    SELECT 1
    FROM orders o
    WHERE o.cust_id = c.cust_id
)
ORDER BY c.cust_name;

-- Expected result:
--  cust_name | city
-- -----------+------
--  LexCorp   | Austin


-- ============================================================================
-- QUERY 17: String Functions
-- Task: Extract the domain-like part from customer names and convert to uppercase.
-- ============================================================================

SELECT cust_name,
       UPPER(SPLIT_PART(cust_name, ' ', 2)) AS name_suffix_upper,
       LENGTH(cust_name) AS name_length
FROM customers
ORDER BY name_length;

-- Expected result:
--  cust_name         | name_suffix_upper | name_length
-- -------------------+-------------------+------------
--  Oscorp            | OSCORP            | 6
--  LexCorp           | LEXCORP           | 7
--  Initech           | INITECH           | 7
--  Acme Corp         | CORP              | 9
--  Globex Inc        | INC               | 10
--  Umbrella Corp     | CORP              | 13
--  Stark Industries  | INDUSTRIES        | 16
--  Wayne Enterprises | ENTERPRISES       | 17

-- NOTE: SPLIT_PART is PostgreSQL-specific. For MySQL use SUBSTRING_INDEX,
-- for SQL Server use a combination of CHARINDEX and SUBSTRING.


-- ============================================================================
-- QUERY 18: Date Functions
-- Task: Calculate years of service for each employee as of today.
-- ============================================================================

SELECT emp_name, hire_date,
       EXTRACT(YEAR FROM AGE(CURRENT_DATE, hire_date)) AS years_of_service,
       DATE_TRUNC('month', hire_date) AS hire_month
FROM employees
ORDER BY hire_date;

-- Expected result (dates relative to CURRENT_DATE; sample for 2026-07-15):
--  emp_name | hire_date  | years_of_service | hire_month
-- ----------+------------+-----------------+------------
--  Hank     | 2017-05-30 | 9                | 2017-05-01
--  Charlie  | 2018-07-22 | 7                | 2018-07-01
--  Alice    | 2019-03-15 | 7                | 2019-03-01
--  Ivy      | 2019-08-20 | 6                | 2019-08-01
--  Diana    | 2019-11-01 | 6                | 2019-11-01

-- NOTE: AGE() and DATE_TRUNC() are PostgreSQL. For MySQL use TIMESTAMPDIFF(YEAR, ...)
-- and DATE_FORMAT(). For SQL Server use DATEDIFF(YEAR, ...) and DATEFROMPARTS().


-- ============================================================================
-- QUERY 19: COALESCE / NULL Handling
-- Task: Show each employee's manager name, or 'No Manager' if none.
-- ============================================================================

SELECT e.emp_name AS employee,
       COALESCE(m.emp_name, 'No Manager') AS manager
FROM employees e
LEFT JOIN employees m ON e.manager_id = m.emp_id
ORDER BY e.emp_name;

-- Expected result (first 5 rows):
--  employee | manager
-- ----------+-----------
--  Alice    | No Manager
--  Bob      | Alice
--  Charlie  | No Manager
--  Diana    | Charlie
--  Eve      | No Manager


-- ============================================================================
-- QUERY 20: Multi-Table JOIN
-- Task: Produce a flat order report: order_id, customer name, product name,
--        quantity, unit_price, line total.
-- ============================================================================

SELECT o.order_id,
       c.cust_name,
       p.prod_name,
       oi.quantity,
       oi.unit_price,
       ROUND(oi.quantity * oi.unit_price, 2) AS line_total
FROM orders o
JOIN customers c    ON o.cust_id = c.cust_id
JOIN order_items oi ON o.order_id = oi.order_id
JOIN products p     ON oi.prod_id = p.prod_id
ORDER BY o.order_id, p.prod_name;

-- Expected result (first 5 rows):
--  order_id | cust_name  | prod_name | quantity | unit_price | line_total
-- ----------+------------+-----------+----------+------------+-----------
--  1        | Acme Corp  | Gadget X  | 1        | 49.99      | 49.99
--  1        | Acme Corp  | Widget A  | 5        | 19.99      | 99.95
--  2        | Acme Corp  | Widget B  | 10       | 24.99      | 249.90
--  3        | Globex Inc | Widget A  | 5        | 19.99      | 99.95
--  4        | Initech    | Gadget Y  | 5        | 79.99      | 399.95


-- ============================================================================
-- QUERY 21: Aggregate with GROUP BY and ORDER BY
-- Task: Total revenue per customer, ordered by revenue descending.
-- ============================================================================

SELECT c.cust_name,
       COUNT(DISTINCT o.order_id) AS order_count,
       ROUND(SUM(o.total_amount), 2) AS total_revenue
FROM customers c
JOIN orders o ON c.cust_id = o.cust_id
GROUP BY c.cust_name
ORDER BY total_revenue DESC;

-- Expected result:
--  cust_name        | order_count | total_revenue
-- ------------------+-------------+--------------
--  Acme Corp        | 4           | 604.79
--  Initech          | 2           | 699.93
--  Stark Industries | 1           | 499.95
--  Globex Inc       | 2           | 249.95
--  Oscorp           | 1           | 399.96
--  Umbrella Corp    | 1           | 199.99
--  Wayne Enterprises| 1           | 59.98


-- ============================================================================
-- QUERY 22: Top-N per Group
-- Task: Find the highest-paid employee in each department.
-- ============================================================================

SELECT dept_name, emp_name, salary
FROM (
    SELECT d.dept_name, e.emp_name, e.salary,
           ROW_NUMBER() OVER (PARTITION BY e.dept_id ORDER BY e.salary DESC) AS rn
    FROM employees e
    JOIN departments d ON e.dept_id = d.dept_id
) ranked
WHERE rn = 1
ORDER BY salary DESC;

-- Expected result:
--  dept_name   | emp_name | salary
-- -------------+----------+--------
--  Data        | Hank     | 140000
--  Finance     | Ivy      | 135000
--  Engineering | Alice    | 120000
--  Product     | Eve      | 105000
--  Marketing   | Grace    |  95000


-- ============================================================================
-- QUERY 23: Recursive CTE
-- Task: Build the management chain for a specific employee (e.g., Bob, emp_id=2).
-- ============================================================================

WITH RECURSIVE mgr_chain AS (
    -- Anchor: start with Bob
    SELECT emp_id, emp_name, manager_id, 1 AS level
    FROM employees
    WHERE emp_id = 2

    UNION ALL

    -- Recursive: find the manager of the current employee
    SELECT e.emp_id, e.emp_name, e.manager_id, mc.level + 1
    FROM employees e
    JOIN mgr_chain mc ON e.emp_id = mc.manager_id
)
SELECT emp_name, level
FROM mgr_chain
ORDER BY level;

-- Expected result:
--  emp_name | level
-- ----------+------
--  Bob      | 1
--  Alice    | 2

-- NOTE: WITH RECURSIVE is PostgreSQL / MySQL 8+ / SQL Server syntax.
-- Oracle uses CONNECT BY PRIOR instead.


-- ============================================================================
-- QUERY 24: Pivot / Conditional Aggregation
-- Task: Show the count of employees per department as columns (pivot).
-- ============================================================================

SELECT
    COUNT(*) FILTER (WHERE dept_id = 1) AS engineering,
    COUNT(*) FILTER (WHERE dept_id = 2) AS data,
    COUNT(*) FILTER (WHERE dept_id = 3) AS product,
    COUNT(*) FILTER (WHERE dept_id = 4) AS marketing,
    COUNT(*) FILTER (WHERE dept_id = 5) AS finance
FROM employees;

-- Expected result:
--  engineering | data | product | marketing | finance
-- -------------+------+---------+-----------+--------
--  4           | 3    | 2       | 2         | 1

-- NOTE: FILTER clause is PostgreSQL-specific. For MySQL/SQL Server use:
-- SELECT
--     SUM(CASE WHEN dept_id = 1 THEN 1 ELSE 0 END) AS engineering, ...


-- ============================================================================
-- QUERY 25: Cumulative Distribution / Percentile
-- Task: Assign each employee a percentile rank based on salary across the company.
-- ============================================================================

SELECT emp_name, salary,
       ROUND(
           PERCENT_RANK() OVER (ORDER BY salary) * 100, 1
       ) AS percentile_pct,
       NTILE(4) OVER (ORDER BY salary) AS salary_quartile
FROM employees
ORDER BY salary DESC;

-- Expected result:
--  emp_name | salary  | percentile_pct | salary_quartile
-- ----------+---------+---------------+----------------
--  Hank     | 140000  | 100.0         | 1
--  Ivy      | 135000  | 90.9          | 1
--  Charlie  | 130000  | 81.8          | 1
--  Diana    | 125000  | 72.7          | 2
--  Alice    | 120000  | 63.6          | 2
--  Karen    | 118000  | 54.5          | 2
--  Frank    | 115000  | 45.5          | 3
--  Bob      | 110000  | 36.4          | 3
--  Eve      | 105000  | 27.3          | 3
--  Jack     | 100000  | 18.2          | 4
--  Grace    |  95000  | 9.1           | 4
--  Leo      |  92000  | 0.0           | 4


-- ============================================================================
-- QUERY 26: Find Duplicates
-- Task: Find customers in cities that have more than one customer.
-- ============================================================================

SELECT city, COUNT(*) AS customer_count,
       STRING_AGG(cust_name, ', ' ORDER BY cust_name) AS customers
FROM customers
GROUP BY city
HAVING COUNT(*) > 1
ORDER BY customer_count DESC;

-- Expected result:
--  city     | customer_count | customers
-- ----------+---------------+------------------------------
--  New York | 3             | Acme Corp, Oscorp, Umbrella Corp
--  Chicago  | 2             | Globex Inc, Wayne Enterprises
--  Austin   | 2             | Initech, LexCorp

-- NOTE: STRING_AGG is PostgreSQL. For MySQL use GROUP_CONCAT,
-- for SQL Server use STRING_AGG (2017+) or FOR XML PATH.


-- ============================================================================
-- QUERY 27: DELETE with JOIN (or USING)
-- Task: Delete all orders for customers who have not signed up yet
--       (hypothetical cleanup — no rows match in sample data).
-- ============================================================================

-- Show rows that would be deleted first (always preview before DELETE):
SELECT o.order_id, o.cust_id, o.order_date
FROM orders o
LEFT JOIN customers c ON o.cust_id = c.cust_id
WHERE c.cust_id IS NULL;

-- Expected result: (empty — all orders have valid customers in sample data)
--  order_id | cust_id | order_date
-- ----------+---------+-----------
-- (0 rows)

-- The actual DELETE (PostgreSQL syntax):
-- DELETE FROM orders o
-- USING orders o2
-- LEFT JOIN customers c ON o2.cust_id = c.cust_id
-- WHERE o.order_id = o2.order_id AND c.cust_id IS NULL;


-- ============================================================================
-- QUERY 28: UPDATE with JOIN
-- Task: Give a 10% salary raise to all employees in the Data department.
--       (Show SELECT first to preview, then the UPDATE.)
-- ============================================================================

-- Preview:
SELECT e.emp_name, e.salary, ROUND(e.salary * 1.10, 2) AS new_salary
FROM employees e
JOIN departments d ON e.dept_id = d.dept_id
WHERE d.dept_name = 'Data';

-- Expected preview:
--  emp_name | salary  | new_salary
-- ----------+---------+-----------
--  Charlie  | 130000  | 143000.00
--  Diana    | 125000  | 137500.00
--  Hank     | 140000  | 154000.00

-- The actual UPDATE (PostgreSQL syntax):
-- UPDATE employees e
-- SET salary = ROUND(salary * 1.10, 2)
-- FROM departments d
-- WHERE e.dept_id = d.dept_id AND d.dept_name = 'Data';


-- ============================================================================
-- QUERY 29: Moving Average (Window Function)
-- Task: 3-month moving average of order totals per customer (Acme Corp, cust_id=1).
-- ============================================================================

SELECT order_id, order_date, total_amount,
       ROUND(
           AVG(total_amount) OVER (
               PARTITION BY cust_id
               ORDER BY order_date
               ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
           ), 2
       ) AS moving_avg_3
FROM orders
WHERE cust_id = 1
ORDER BY order_date;

-- Expected result:
--  order_id | order_date | total_amount | moving_avg_3
-- ----------+------------+--------------+-------------
--  1        | 2022-01-10 | 149.95       | 149.95
--  2        | 2022-02-15 | 249.90       | 199.93
--  5        | 2022-04-10 | 79.99        | 159.95
--  11       | 2022-09-10 | 124.95       | 151.61


-- ============================================================================
-- QUERY 30: Index Creation and EXPLAIN
-- Task: Create an index to speed up queries filtering by hire_date,
--        then show the query plan.
-- ============================================================================

-- Create the index:
-- CREATE INDEX idx_employees_hire_date ON employees(hire_date);

-- Show the query plan (does not execute the query):
-- EXPLAIN SELECT emp_name, salary FROM employees WHERE hire_date >= '2020-01-01';

-- Expected EXPLAIN output (conceptual):
--  QUERY PLAN
--  -------------------------------------------------------------------
--  Index Scan using idx_employees_hire_date on employees
--    Index Cond: (hire_date >= '2020-01-01'::date)

-- NOTE: EXPLAIN is informational only. EXPLAIN ANALYZE actually runs the query
-- and reports real timing. Use EXPLAIN (FORMAT JSON) for machine-readable plans.


-- ============================================================================
-- QUERY 31: FULL OUTER JOIN
-- Task: Show all employees and all departments, including unmatched rows on both sides.
--       (Add a department with no employees and an employee with no department.)
-- ============================================================================

-- Add a department with no employees and an employee with NULL dept_id
INSERT INTO departments VALUES (6, 'Legal');
INSERT INTO employees VALUES (13, 'Mona', NULL, 88000, '2023-01-15', NULL);

SELECT COALESCE(e.emp_name, '(no employees)') AS emp_name,
       COALESCE(d.dept_name, '(no department)') AS dept_name
FROM departments d
FULL OUTER JOIN employees e ON d.dept_id = e.dept_id
ORDER BY dept_name, emp_name;

-- Expected result:
--  emp_name      | dept_name
-- ---------------+-------------
--  Hank          | Data
--  Charlie       | Data
--  Diana         | Data
--  Alice         | Engineering
--  Bob           | Engineering
--  Frank         | Engineering
--  Karen         | Engineering
--  Ivy           | Finance
--  (no employees)| Legal
--  Grace         | Marketing
--  Leo           | Marketing
--  Mona          | (no department)
--  Eve           | Product
--  Jack          | Product

-- Cleanup the extra rows:
-- DELETE FROM employees WHERE emp_id = 13;
-- DELETE FROM departments WHERE dept_id = 6;


-- ============================================================================
-- QUERY 32: CROSS JOIN (Cartesian Product)
-- Task: Generate all possible employee-product pairings for a small subset.
--       Useful for scenario analysis or generating test data.
-- ============================================================================

SELECT e.emp_name, p.prod_name
FROM (SELECT emp_name FROM employees WHERE emp_id <= 3) e
CROSS JOIN (SELECT prod_name FROM products WHERE prod_id <= 2) p
ORDER BY e.emp_name, p.prod_name;

-- Expected result:
--  emp_name | prod_name
-- ----------+----------
--  Alice    | Widget A
--  Alice    | Widget B
--  Bob      | Widget A
--  Bob      | Widget B
--  Charlie  | Widget A
--  Charlie  | Widget B


-- ============================================================================
-- QUERY 33: FIRST_VALUE / LAST_VALUE / NTH_VALUE
-- Task: For each department, show the first-hired and last-hired employee names
--        alongside every employee row.
-- ============================================================================

SELECT dept_id, emp_name, hire_date,
       FIRST_VALUE(emp_name) OVER (
           PARTITION BY dept_id ORDER BY hire_date
           ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
       ) AS first_hired,
       LAST_VALUE(emp_name) OVER (
           PARTITION BY dept_id ORDER BY hire_date
           ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
       ) AS last_hired
FROM employees
WHERE dept_id IS NOT NULL
ORDER BY dept_id, hire_date;

-- Expected result for dept_id=1 (Engineering):
--  dept_id | emp_name | hire_date  | first_hired | last_hired
-- ---------+----------+------------+-------------+-----------
--  1       | Alice    | 2019-03-15 | Alice       | Frank
--  1       | Bob      | 2020-01-10 | Alice       | Frank
--  1       | Karen    | 2020-04-18 | Alice       | Frank
--  1       | Frank    | 2020-09-01 | Alice       | Frank


-- ============================================================================
-- QUERY 34: JSON Operations
-- Task: Build a JSON object per employee and extract/query JSON fields.
-- ============================================================================

-- Build JSON per employee
SELECT emp_name,
       JSON_BUILD_OBJECT(
           'name', emp_name,
           'dept_id', dept_id,
           'salary', salary,
           'hire_date', hire_date
       ) AS employee_json
FROM employees
WHERE emp_id <= 3;

-- Expected result:
--  emp_name | employee_json
-- ----------+----------------------------------------------------------
--  Alice    | {"name":"Alice","dept_id":1,"salary":120000,"hire_date":"2019-03-15"}
--  Bob      | {"name":"Bob","dept_id":1,"salary":110000,"hire_date":"2020-01-10"}
--  Charlie  | {"name":"Charlie","dept_id":2,"salary":130000,"hire_date":"2018-07-22"}

-- Extract from JSON array (conceptual):
-- SELECT JSON_ARRAY_ELEMENTS('[1,2,3]'::json);

-- NOTE: JSON_BUILD_OBJECT is PostgreSQL. For MySQL use JSON_OBJECT(),
-- for SQL Server use FOR JSON PATH.


-- ============================================================================
-- QUERY 35: ROLLUP / CUBE / GROUPING SETS
-- Task: Generate subtotals and grand total of salaries by department.
-- ============================================================================

SELECT COALESCE(d.dept_name, 'ALL DEPTS') AS dept_name,
       COUNT(*) AS emp_count,
       SUM(e.salary) AS total_salary,
       ROUND(AVG(e.salary), 2) AS avg_salary
FROM employees e
JOIN departments d ON e.dept_id = d.dept_id
GROUP BY ROLLUP(d.dept_name)
ORDER BY d.dept_name NULLS LAST;

-- Expected result:
--  dept_name   | emp_count | total_salary | avg_salary
-- -------------+-----------+--------------+-----------
--  Data        | 3         | 395000       | 131666.67
--  Engineering | 4         | 463000       | 115750.00
--  Finance     | 1         | 135000       | 135000.00
--  Marketing   | 2         | 187000       |  93500.00
--  Product     | 2         | 205000       | 102500.00
--  ALL DEPTS   | 12        | 1385000      | 115416.67

-- NOTE: ROLLUP is supported in PostgreSQL, MySQL 8+, SQL Server, Oracle.
-- CUBE generates all possible combinations; GROUPING SETS for specific combos.


-- ============================================================================
-- QUERY 36: LATERAL JOIN (CROSS APPLY equivalent)
-- Task: For each department, show the top 2 highest-paid employees using LATERAL.
-- ============================================================================

SELECT d.dept_name, top.emp_name, top.salary
FROM departments d
CROSS JOIN LATERAL (
    SELECT emp_name, salary
    FROM employees e
    WHERE e.dept_id = d.dept_id
    ORDER BY salary DESC
    LIMIT 2
) top
ORDER BY d.dept_name, top.salary DESC;

-- Expected result:
--  dept_name   | emp_name | salary
-- -------------+----------+--------
--  Data        | Hank     | 140000
--  Data        | Charlie  | 130000
--  Engineering | Alice    | 120000
--  Engineering | Karen    | 118000
--  Finance     | Ivy      | 135000
--  Marketing   | Grace    |  95000
--  Marketing   | Leo      |  92000
--  Product     | Eve      | 105000
--  Product     | Jack     | 100000

-- NOTE: LATERAL is PostgreSQL. SQL Server uses CROSS APPLY / OUTER APPLY.
-- MySQL 8+ supports LATERAL. Oracle uses CROSS APPLY.


-- ============================================================================
-- QUERY 37: MERGE / UPSERT
-- Task: Synchronize a staging table into the target table (conceptual).
--       Insert new rows, update existing ones based on primary key.
-- ============================================================================

-- Create a staging table with one new employee and one updated salary
CREATE TEMP TABLE employees_staging AS
SELECT * FROM employees WHERE emp_id <= 2;
UPDATE employees_staging SET salary = 125000 WHERE emp_id = 1;  -- Alice gets a raise
INSERT INTO employees_staging VALUES (14, 'Nina', 2, 115000, '2023-03-01', 3);  -- New hire

-- MERGE statement (PostgreSQL 15+):
-- MERGE INTO employees e
-- USING employees_staging s ON e.emp_id = s.emp_id
-- WHEN MATCHED THEN
--     UPDATE SET emp_name = s.emp_name, dept_id = s.dept_id,
--                salary = s.salary, hire_date = s.hire_date, manager_id = s.manager_id
-- WHEN NOT MATCHED THEN
--     INSERT (emp_id, emp_name, dept_id, salary, hire_date, manager_id)
--     VALUES (s.emp_id, s.emp_name, s.dept_id, s.salary, s.hire_date, s.manager_id);

-- Alternative UPSERT using ON CONFLICT (PostgreSQL):
-- INSERT INTO employees (emp_id, emp_name, dept_id, salary, hire_date, manager_id)
-- SELECT emp_id, emp_name, dept_id, salary, hire_date, manager_id FROM employees_staging
-- ON CONFLICT (emp_id) DO UPDATE SET
--     emp_name = EXCLUDED.emp_name,
--     dept_id = EXCLUDED.dept_id,
--     salary = EXCLUDED.salary,
--     hire_date = EXCLUDED.hire_date,
--     manager_id = EXCLUDED.manager_id;

-- Preview what would change:
SELECT 'UPDATE' AS action, e.emp_id, e.emp_name, e.salary AS old_salary, s.salary AS new_salary
FROM employees e JOIN employees_staging s ON e.emp_id = s.emp_id
WHERE e.salary <> s.salary
UNION ALL
SELECT 'INSERT' AS action, s.emp_id, s.emp_name, NULL, s.salary
FROM employees_staging s
WHERE NOT EXISTS (SELECT 1 FROM employees e WHERE e.emp_id = s.emp_id);

-- Expected preview:
--  action | emp_id | emp_name | old_salary | new_salary
-- --------+--------+----------+------------+-----------
--  UPDATE | 1      | Alice    | 120000     | 125000
--  INSERT | 14     | Nina     | NULL       | 115000

-- Cleanup:
-- DROP TABLE IF EXISTS employees_staging;

-- NOTE: MERGE is PostgreSQL 15+, SQL Server, Oracle. MySQL uses
-- INSERT ... ON DUPLICATE KEY UPDATE or REPLACE INTO.


-- ============================================================================
-- QUERY 38: Temporal / Date Range Queries
-- Task: Find orders placed in Q1 2022 (January through March).
--       Also show how to generate a date series.
-- ============================================================================

-- Orders in Q1 2022
SELECT order_id, cust_id, order_date, total_amount
FROM orders
WHERE order_date BETWEEN '2022-01-01' AND '2022-03-31'
ORDER BY order_date;

-- Expected result:
--  order_id | cust_id | order_date | total_amount
-- ----------+---------+------------+-------------
--  1        | 1       | 2022-01-10 | 149.95
--  3        | 2       | 2022-01-20 | 99.98
--  2        | 1       | 2022-02-15 | 249.90
--  4        | 3       | 2022-03-05 | 399.96

-- Generate a date series (PostgreSQL):
-- SELECT generate_series('2022-01-01'::date, '2022-01-07'::date, '1 day'::interval) AS date;

-- Count orders by month:
SELECT TO_CHAR(order_date, 'YYYY-MM') AS month,
       COUNT(*) AS order_count,
       ROUND(SUM(total_amount), 2) AS monthly_revenue
FROM orders
GROUP BY TO_CHAR(order_date, 'YYYY-MM')
ORDER BY month;

-- Expected result:
--  month   | order_count | monthly_revenue
-- ---------+-------------+----------------
--  2022-01 | 2           | 249.93
--  2022-02 | 1           | 249.90
--  2022-03 | 1           | 399.96
--  2022-04 | 2           | 279.98
--  2022-05 | 1           | 499.95
--  2022-06 | 1           | 149.97
--  2022-07 | 1           | 59.98
--  2022-08 | 1           | 299.97
--  2022-09 | 1           | 124.95
--  2022-10 | 1           | 399.96


-- ============================================================================
-- QUERY 39: Views and Materialized Views
-- Task: Create a view for a commonly-used query, then a materialized view
--        for pre-computed aggregations.
-- ============================================================================

-- Regular view (computed at query time)
-- CREATE VIEW vw_employee_summary AS
-- SELECT d.dept_name,
--        COUNT(e.emp_id) AS emp_count,
--        ROUND(AVG(e.salary), 2) AS avg_salary,
--        MAX(e.salary) AS max_salary
-- FROM departments d
-- LEFT JOIN employees e ON d.dept_id = e.dept_id
-- GROUP BY d.dept_name;

-- Query the view:
-- SELECT * FROM vw_employee_summary ORDER BY avg_salary DESC;

-- Materialized view (pre-computed, needs refresh)
-- CREATE MATERIALIZED VIEW mv_monthly_sales AS
-- SELECT TO_CHAR(order_date, 'YYYY-MM') AS month,
--        COUNT(*) AS order_count,
--        ROUND(SUM(total_amount), 2) AS total_revenue
-- FROM orders
-- GROUP BY TO_CHAR(order_date, 'YYYY-MM');

-- Refresh when source data changes:
-- REFRESH MATERIALIZED VIEW mv_monthly_sales;

-- Query the materialized view:
-- SELECT * FROM mv_monthly_sales ORDER BY month;

-- NOTE: Materialized views are supported in PostgreSQL, Oracle, SQL Server
-- (as indexed views). MySQL does not support materialized views natively.


-- ============================================================================
-- QUERY 40: Transaction Control and ACID
-- Task: Demonstrate a transaction that transfers an employee between departments
--        with proper commit/rollback semantics.
-- ============================================================================

-- Start a transaction
-- BEGIN;

-- Move Bob from Engineering (dept_id=1) to Data (dept_id=2)
-- UPDATE employees SET dept_id = 2 WHERE emp_id = 2;

-- Verify the change within the transaction
-- SELECT emp_name, dept_id FROM employees WHERE emp_id = 2;
-- Expected: Bob | 2

-- If something goes wrong, rollback:
-- ROLLBACK;
-- Now Bob is back in Engineering.

-- If everything is correct, commit:
-- COMMIT;

-- Conceptual: transfer with audit logging
-- BEGIN;
-- UPDATE employees SET dept_id = 2 WHERE emp_id = 2;
-- INSERT INTO dept_transfer_log (emp_id, from_dept, to_dept, transfer_date)
-- VALUES (2, 1, 2, CURRENT_DATE);
-- COMMIT;

-- NOTE: Transaction semantics are standard across all RDBMS.
-- PostgreSQL, MySQL (InnoDB), SQL Server, Oracle all support BEGIN/COMMIT/ROLLBACK.
-- SAVEPOINT allows partial rollback within a transaction.


-- ============================================================================
-- END OF FILE
-- ============================================================================
