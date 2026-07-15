"""
============================================================================
Data Engineer PySpark Interview — Core ETL Patterns Demo
============================================================================
Covers: DataFrame creation, select/filter/where, column operations,
        aggregations, joins, window functions, UDFs, handling nulls,
        date operations, pivot, explode, partition writing, and
        common interview ETL patterns.

Run: python spark-basic.py
Requires: pyspark>=3.5.0
============================================================================
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from typing import List

from pyspark.sql import DataFrame, SparkSession, Window
from pyspark.sql import functions as F
from pyspark.sql import types as T


# ═══════════════════════════════════════════════════════════════════════════════
# 0. SPARK SESSION — the entry point for every PySpark job
# ═══════════════════════════════════════════════════════════════════════════════

def build_spark(app_name: str = "pyspark-interview-demo") -> SparkSession:
    """Create a local Spark session suitable for interview demos."""
    return (
        SparkSession.builder
        .appName(app_name)
        .master("local[*]")
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.sql.adaptive.enabled", "true")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .getOrCreate()
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 1. DATAFRAME CREATION — from lists, RDD, schema definition
# ═══════════════════════════════════════════════════════════════════════════════

def demo_create_dataframes(spark: SparkSession) -> None:
    print("=" * 60)
    print("1. DATAFRAME CREATION")
    print("=" * 60)

    # --- 1a. From list of tuples (schema inferred) ---
    data: List[tuple] = [
        (1, "Alice",   "Engineering", 120000.0, "2019-03-15"),
        (2, "Bob",     "Engineering", 110000.0, "2020-01-10"),
        (3, "Charlie", "Data",        130000.0, "2018-07-22"),
        (4, "Diana",   "Data",        125000.0, "2019-11-01"),
        (5, "Eve",     "Product",     105000.0, "2021-06-15"),
        (6, "Frank",   "Engineering", 115000.0, "2020-09-01"),
        (7, "Grace",   "Marketing",    95000.0, "2022-02-14"),
        (8, "Hank",    "Data",        140000.0, "2017-05-30"),
    ]
    columns = ["emp_id", "emp_name", "dept", "salary", "hire_date"]

    df = spark.createDataFrame(data, schema=columns)
    df.show(5, truncate=False)
    df.printSchema()

    # --- 1b. With explicit schema (better type control) ---
    schema = T.StructType([
        T.StructField("emp_id",    T.IntegerType(),  False),
        T.StructField("emp_name",  T.StringType(),   False),
        T.StructField("dept",      T.StringType(),   False),
        T.StructField("salary",    T.DoubleType(),   False),
        T.StructField("hire_date", T.StringType(),   False),
    ])
    df_typed = spark.createDataFrame(data, schema=schema) \
        .withColumn("hire_date", F.to_date("hire_date", "yyyy-MM-dd"))
    print("Explicit schema (with to_date cast):")
    df_typed.printSchema()

    # --- 1c. From JSON / CSV (conceptual — using inline JSON) ---
    json_str = """{"emp_id":9,"emp_name":"Ivy","dept":"Finance","salary":135000,"hire_date":"2019-08-20"}"""
    json_rdd = spark.sparkContext.parallelize([json_str])
    df_json = spark.read.json(json_rdd, schema=schema)
    print("From JSON:")
    df_json.show()

    # --- 1d. Range (generate rows) ---
    df_range = spark.range(1, 6).withColumn("squared", F.col("id") ** 2)
    print("spark.range:")
    df_range.show()


# ═══════════════════════════════════════════════════════════════════════════════
# 2. SELECT, FILTER, WHERE, COLUMN OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════════

def demo_select_filter(spark: SparkSession) -> None:
    print("\n" + "=" * 60)
    print("2. SELECT / FILTER / COLUMN OPERATIONS")
    print("=" * 60)

    df = _build_employee_df(spark)

    # --- select specific columns ---
    df.select("emp_name", "salary").show(5)

    # --- select with column expressions ---
    df.select(
        F.col("emp_name"),
        F.col("salary"),
        (F.col("salary") * 1.10).alias("salary_after_raise"),
        F.col("hire_date"),
    ).show(5)

    # --- filter / where (synonyms) ---
    print("Engineers earning > 110k:")
    df.filter((F.col("dept") == "Engineering") & (F.col("salary") > 110000)).show()

    print("Data OR Product department:")
    df.where(F.col("dept").isin("Data", "Product")).show()

    # --- like / rlike (regex) ---
    print("Names starting with 'A' or 'C':")
    df.filter(F.col("emp_name").rlike("^[AC]")).show()

    # --- between ---
    print("Salary between 100k and 120k:")
    df.filter(F.col("salary").between(100000, 120000)).show()

    # --- when / otherwise (CASE WHEN equivalent) ---
    df.withColumn(
        "salary_band",
        F.when(F.col("salary") >= 130000, "Executive")
         .when(F.col("salary") >= 115000, "Senior")
         .when(F.col("salary") >= 100000, "Mid")
         .otherwise("Junior"),
    ).select("emp_name", "salary", "salary_band").show()

    # --- withColumnRenamed ---
    df.withColumnRenamed("dept", "department").show(3)

    # --- drop ---
    df.drop("hire_date").show(3)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. AGGREGATIONS — groupBy, agg, count, sum, avg, min, max
# ═══════════════════════════════════════════════════════════════════════════════

def demo_aggregations(spark: SparkSession) -> None:
    print("\n" + "=" * 60)
    print("3. AGGREGATIONS")
    print("=" * 60)

    df = _build_employee_df(spark)

    # --- Simple count ---
    print(f"Total employees: {df.count()}")

    # --- groupBy + count ---
    df.groupBy("dept").count().orderBy("count", ascending=False).show()

    # --- groupBy + multiple aggregates ---
    df.groupBy("dept").agg(
        F.count("*").alias("emp_count"),
        F.round(F.avg("salary"), 2).alias("avg_salary"),
        F.max("salary").alias("max_salary"),
        F.min("salary").alias("min_salary"),
        F.sum("salary").alias("total_salary"),
    ).orderBy("avg_salary", ascending=False).show()

    # --- agg on entire DataFrame (no groupBy) ---
    df.agg(
        F.avg("salary").alias("company_avg"),
        F.stddev("salary").alias("salary_stddev"),
    ).show()

    # --- countDistinct / approx_count_distinct ---
    df.agg(
        F.countDistinct("dept").alias("distinct_depts"),
        F.approx_count_distinct("salary").alias("approx_distinct_salaries"),
    ).show()

    # --- collect_list / collect_set ---
    df.groupBy("dept").agg(
        F.collect_list("emp_name").alias("all_names"),
        F.collect_set("emp_name").alias("unique_names"),  # same as list here
    ).show(truncate=False)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. JOINS — inner, left, right, full outer, anti, semi
# ═══════════════════════════════════════════════════════════════════════════════

def demo_joins(spark: SparkSession) -> None:
    print("\n" + "=" * 60)
    print("4. JOINS")
    print("=" * 60)

    emp = _build_employee_df(spark)

    dept_data = [
        ("Engineering", "NYC", "Alice"),
        ("Data",        "SF",  "Charlie"),
        ("Product",     "NYC", "Eve"),
        ("Marketing",   "CHI", "Grace"),
        ("Finance",     "NYC", "Ivy"),
        ("Legal",       "DC",  None),   # no employees in Legal
    ]
    dept = spark.createDataFrame(dept_data, ["dept_name", "office", "manager"])

    # --- Inner join (only matching rows) ---
    print("INNER JOIN:")
    emp.join(dept, emp.dept == dept.dept_name, "inner") \
       .select("emp_name", "dept", "office", "manager").show()

    # --- Left join (all employees, even if dept missing) ---
    print("LEFT JOIN:")
    emp.join(dept, emp.dept == dept.dept_name, "left") \
       .select("emp_name", "dept", "office").show()

    # --- Right join (all departments, even if no employees) ---
    print("RIGHT JOIN:")
    emp.join(dept, emp.dept == dept.dept_name, "right") \
       .select(F.coalesce(F.col("emp_name"), F.lit("(none)")).alias("emp_name"),
               F.col("dept_name").alias("dept"),
               "office").show()

    # --- Full outer join ---
    print("FULL OUTER JOIN:")
    emp.join(dept, emp.dept == dept.dept_name, "full_outer") \
       .select(F.coalesce("emp_name", F.lit("(none)")).alias("emp_name"),
               F.coalesce("dept", "dept_name").alias("dept")).show()

    # --- Anti join (employees whose dept is NOT in dept table) ---
    print("ANTI JOIN (employees with no dept match):")
    emp.join(dept, emp.dept == dept.dept_name, "anti").show()

    # --- Semi join (employees whose dept IS in dept table — like EXISTS) ---
    print("SEMI JOIN:")
    emp.join(dept, emp.dept == dept.dept_name, "semi").show()

    # --- Broadcast hint (for small tables) ---
    from pyspark.sql.functions import broadcast
    print("BROADCAST JOIN:")
    emp.join(broadcast(dept), emp.dept == dept.dept_name, "inner") \
       .select("emp_name", "office").show()


# ═══════════════════════════════════════════════════════════════════════════════
# 5. WINDOW FUNCTIONS — row_number, rank, dense_rank, lag, lead, running total
# ═══════════════════════════════════════════════════════════════════════════════

def demo_window_functions(spark: SparkSession) -> None:
    print("\n" + "=" * 60)
    print("5. WINDOW FUNCTIONS")
    print("=" * 60)

    df = _build_employee_df(spark)

    # --- row_number: unique rank within partition ---
    win_dept_salary = Window.partitionBy("dept").orderBy(F.col("salary").desc())
    df.withColumn("rank_in_dept", F.row_number().over(win_dept_salary)) \
      .select("dept", "emp_name", "salary", "rank_in_dept") \
      .orderBy("dept", "rank_in_dept").show()

    # --- rank vs dense_rank ---
    df.withColumn("rank_", F.rank().over(win_dept_salary)) \
      .withColumn("dense_rank_", F.dense_rank().over(win_dept_salary)) \
      .select("dept", "emp_name", "salary", "rank_", "dense_rank_") \
      .orderBy("dept", "salary", ascending=[True, False]).show()

    # --- lag / lead (previous / next row) ---
    win_hire = Window.partitionBy("dept").orderBy("hire_date")
    df.withColumn("prev_hire", F.lag("hire_date", 1).over(win_hire)) \
      .withColumn("next_hire", F.lead("hire_date", 1).over(win_hire)) \
      .select("dept", "emp_name", "hire_date", "prev_hire", "next_hire") \
      .orderBy("dept", "hire_date").show()

    # --- Running total (rowsBetween / rangeBetween) ---
    win_total = Window.orderBy("hire_date").rowsBetween(Window.unboundedPreceding, Window.currentRow)
    df.withColumn("running_total_salary", F.sum("salary").over(win_total)) \
      .select("emp_name", "hire_date", "salary", "running_total_salary") \
      .orderBy("hire_date").show()

    # --- Moving average (3-row window) ---
    win_moving = Window.orderBy("hire_date").rowsBetween(-2, 0)
    df.withColumn("moving_avg_3", F.round(F.avg("salary").over(win_moving), 2)) \
      .select("emp_name", "hire_date", "salary", "moving_avg_3") \
      .orderBy("hire_date").show()

    # --- first / last / nth_value ---
    df.withColumn("first_hire_in_dept", F.first("hire_date").over(win_hire)) \
      .withColumn("highest_salary_in_dept", F.first("salary").over(win_dept_salary)) \
      .select("dept", "emp_name", "hire_date", "first_hire_in_dept", "highest_salary_in_dept") \
      .orderBy("dept", "hire_date").show()


# ═══════════════════════════════════════════════════════════════════════════════
# 6. UDFs — Python UDF and Pandas UDF (vectorized)
# ═══════════════════════════════════════════════════════════════════════════════

def demo_udfs(spark: SparkSession) -> None:
    print("\n" + "=" * 60)
    print("6. UDFs (User-Defined Functions)")
    print("=" * 60)

    df = _build_employee_df(spark)

    # --- Python UDF (row-at-a-time, slower) ---
    @F.udf(returnType=T.StringType())
    def salary_category(salary: float) -> str:
        if salary >= 130000:
            return "Executive"
        elif salary >= 115000:
            return "Senior"
        elif salary >= 100000:
            return "Mid"
        return "Junior"

    df.withColumn("category_udf", salary_category(F.col("salary"))) \
      .select("emp_name", "salary", "category_udf").show()

    # --- UDF with multiple parameters ---
    @F.udf(returnType=T.StringType())
    def email(name: str, dept: str) -> str:
        return f"{name.lower()}.{dept.lower()}@company.com"

    df.withColumn("email", email(F.col("emp_name"), F.col("dept"))) \
      .select("emp_name", "email").show(5, truncate=False)

    # --- Pandas UDF (vectorized, faster for large datasets) ---
    # Requires: pip install pyarrow
    try:
        from pyspark.sql.functions import pandas_udf
        import pandas as pd

        @pandas_udf(returnType=T.DoubleType())
        def bonus_pandas_udf(salaries: pd.Series) -> pd.Series:
            return salaries * 0.10

        df.withColumn("bonus", bonus_pandas_udf(F.col("salary"))) \
          .select("emp_name", "salary", "bonus").show(5)
    except Exception:
        print("  (Pandas UDF demo skipped — pyarrow may not be available)")


# ═══════════════════════════════════════════════════════════════════════════════
# 7. HANDLING NULLS — na.fill, na.drop, coalesce, isnull
# ═══════════════════════════════════════════════════════════════════════════════

def demo_nulls(spark: SparkSession) -> None:
    print("\n" + "=" * 60)
    print("7. HANDLING NULLS")
    print("=" * 60)

    data = [
        (1, "Alice",   120000.0),
        (2, "Bob",     None),
        (3, "Charlie", 130000.0),
        (4, None,      125000.0),
        (5, "Eve",     105000.0),
    ]
    df = spark.createDataFrame(data, ["id", "name", "salary"])
    print("Original:")
    df.show()

    # --- drop rows with any null ---
    print("dropna(how='any'):")
    df.na.drop(how="any").show()

    # --- drop rows only if specific columns are null ---
    print("dropna(subset=['name']):")
    df.na.drop(subset=["name"]).show()

    # --- fill nulls with constant ---
    print("fillna(0, subset=['salary']):")
    df.na.fill(0, subset=["salary"]).show()

    # --- fill with dict (different values per column) ---
    print("fillna({'name': 'Unknown', 'salary': 0}):")
    df.na.fill({"name": "Unknown", "salary": 0}).show()

    # --- coalesce (first non-null value) ---
    df.withColumn("salary_or_zero", F.coalesce(F.col("salary"), F.lit(0.0))) \
      .withColumn("name_or_unknown", F.coalesce(F.col("name"), F.lit("Unknown"))) \
      .show()

    # --- isnull / isNotNull ---
    df.withColumn("salary_is_null", F.isnull("salary")) \
      .withColumn("name_is_not_null", F.isnotNull("name")) \
      .show()


# ═══════════════════════════════════════════════════════════════════════════════
# 8. DATE / TIMESTAMP OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════════

def demo_dates(spark: SparkSession) -> None:
    print("\n" + "=" * 60)
    print("8. DATE / TIMESTAMP OPERATIONS")
    print("=" * 60)

    df = _build_employee_df(spark)

    # --- date_diff / months_between / datediff ---
    df.withColumn("days_since_hire", F.datediff(F.current_date(), F.col("hire_date"))) \
      .withColumn("months_since_hire", F.months_between(F.current_date(), F.col("hire_date"))) \
      .select("emp_name", "hire_date", "days_since_hire", "months_since_hire") \
      .show()

    # --- date_add / date_sub ---
    df.withColumn("next_review", F.date_add(F.col("hire_date"), 365)) \
      .select("emp_name", "hire_date", "next_review").show()

    # --- year / month / dayofmonth / dayofweek ---
    df.withColumn("hire_year", F.year("hire_date")) \
      .withColumn("hire_month", F.month("hire_date")) \
      .withColumn("hire_day", F.dayofmonth("hire_date")) \
      .withColumn("hire_dow", F.dayofweek("hire_date")) \
      .select("emp_name", "hire_date", "hire_year", "hire_month", "hire_day", "hire_dow") \
      .show()

    # --- date_trunc (truncate to month/year) ---
    df.withColumn("hire_month_start", F.date_trunc("month", "hire_date")) \
      .withColumn("hire_year_start", F.date_trunc("year", "hire_date")) \
      .select("emp_name", "hire_date", "hire_month_start", "hire_year_start") \
      .show()

    # --- to_date / date_format ---
    df.withColumn("hire_date_str", F.date_format("hire_date", "MMM dd, yyyy")) \
      .select("emp_name", "hire_date", "hire_date_str").show()

    # --- unix_timestamp / from_unixtime ---
    df.withColumn("hire_unix", F.unix_timestamp("hire_date", "yyyy-MM-dd")) \
      .withColumn("hire_from_unix", F.from_unixtime("hire_unix", "yyyy-MM-dd")) \
      .select("emp_name", "hire_date", "hire_unix", "hire_from_unix").show()


# ═══════════════════════════════════════════════════════════════════════════════
# 9. STRING OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════════

def demo_strings(spark: SparkSession) -> None:
    print("\n" + "=" * 60)
    print("9. STRING OPERATIONS")
    print("=" * 60)

    df = _build_employee_df(spark)

    # --- concat / concat_ws ---
    df.withColumn("full_info", F.concat_ws(" | ", "emp_name", "dept", F.col("salary").cast("string"))) \
      .select("emp_name", "full_info").show(truncate=False)

    # --- upper / lower / initcap ---
    df.withColumn("name_upper", F.upper("emp_name")) \
      .withColumn("name_lower", F.lower("emp_name")) \
      .withColumn("dept_initcap", F.initcap("dept")) \
      .select("emp_name", "name_upper", "name_lower", "dept_initcap").show()

    # --- substring / length ---
    df.withColumn("first_3_chars", F.substring("emp_name", 1, 3)) \
      .withColumn("name_length", F.length("emp_name")) \
      .select("emp_name", "first_3_chars", "name_length").show()

    # --- split / explode ---
    df.withColumn("name_chars", F.split("emp_name", "")) \
      .withColumn("char", F.explode("name_chars")) \
      .select("emp_name", "char") \
      .filter(F.col("char") != "") \
      .show(10)

    # --- regexp_replace / regexp_extract ---
    df.withColumn("dept_no_spaces", F.regexp_replace("dept", " ", "_")) \
      .select("dept", "dept_no_spaces").show()

    # --- trim / ltrim / rtrim ---
    df_padded = spark.createDataFrame(
        [("  Alice  ",), ("  Bob",), ("Charlie  ",)],
        ["name"]
    )
    df_padded.withColumn("trimmed", F.trim("name")) \
             .withColumn("ltrimmed", F.ltrim("name")) \
             .withColumn("rtrimmed", F.rtrim("name")).show()


# ═══════════════════════════════════════════════════════════════════════════════
# 10. PIVOT / UNPIVOT (stack)
# ═══════════════════════════════════════════════════════════════════════════════

def demo_pivot(spark: SparkSession) -> None:
    print("\n" + "=" * 60)
    print("10. PIVOT / UNPIVOT")
    print("=" * 60)

    # --- PIVOT: rows to columns ---
    sales_data = [
        ("Q1", "Widget",  100),
        ("Q1", "Gadget",  200),
        ("Q2", "Widget",  150),
        ("Q2", "Gadget",  250),
        ("Q3", "Widget",  120),
        ("Q3", "Gadget",  180),
    ]
    df_sales = spark.createDataFrame(sales_data, ["quarter", "product", "revenue"])

    print("Original sales:")
    df_sales.show()

    print("Pivoted (quarters as columns):")
    df_sales.groupBy("product").pivot("quarter").sum("revenue").show()

    # --- Pivot with multiple aggregate values ---
    print("Pivoted with avg:")
    df_sales.groupBy("product").pivot("quarter").agg(F.round(F.avg("revenue"), 2)).show()

    # --- UNPIVOT using stack ---
    pivoted = df_sales.groupBy("product").pivot("quarter").sum("revenue")
    print("Unpivot back using stack:")
    pivoted.select(
        "product",
        F.expr("stack(3, 'Q1', Q1, 'Q2', Q2, 'Q3', Q3) as (quarter, revenue)")
    ).show()


# ═══════════════════════════════════════════════════════════════════════════════
# 11. ARRAY / MAP / STRUCT COLUMNS
# ═══════════════════════════════════════════════════════════════════════════════

def demo_complex_types(spark: SparkSession) -> None:
    print("\n" + "=" * 60)
    print("11. ARRAY / MAP / STRUCT")
    print("=" * 60)

    # --- Array column ---
    df = spark.createDataFrame(
        [(1, ["Python", "SQL", "Spark"]),
         (2, ["Java", "Scala"]),
         (3, ["Python", "R", "SQL", "Airflow"])],
        ["id", "skills"]
    )
    print("Array column:")
    df.show(truncate=False)

    # array_contains
    df.filter(F.array_contains("skills", "Python")).show()

    # size
    df.withColumn("num_skills", F.size("skills")).show()

    # explode
    df.withColumn("skill", F.explode("skills")).show()

    # --- Map column ---
    df_map = spark.createDataFrame(
        [(1, {"Python": 5, "SQL": 4}),
         (2, {"Java": 4, "Scala": 3})],
        ["id", "skill_levels"]
    )
    print("Map column:")
    df_map.show(truncate=False)
    df_map.select("id", F.col("skill_levels").getItem("Python").alias("python_level")).show()

    # explode map
    df_map.select("id", F.explode("skill_levels").alias("skill", "level")).show()

    # --- Struct column ---
    df_struct = spark.createDataFrame(
        [(1, ("Alice", "Engineering")),
         (2, ("Bob", "Data"))],
        ["id", "info"]
    )
    print("Struct column:")
    df_struct.select("id", "info.name", "info._2").show()  # access by name or position


# ═══════════════════════════════════════════════════════════════════════════════
# 12. UNION / UNION BY NAME / DISTINCT / DROP DUPLICATES
# ═══════════════════════════════════════════════════════════════════════════════

def demo_union_distinct(spark: SparkSession) -> None:
    print("\n" + "=" * 60)
    print("12. UNION / DISTINCT / DROP DUPLICATES")
    print("=" * 60)

    df1 = spark.createDataFrame(
        [(1, "Alice", "Engineering"),
         (2, "Bob",   "Engineering")],
        ["id", "name", "dept"]
    )
    df2 = spark.createDataFrame(
        [(3, "Charlie", "Data"),
         (2, "Bob",     "Engineering")],  # duplicate
        ["id", "name", "dept"]
    )

    # --- union (position-based, requires same column order) ---
    print("UNION ALL (includes duplicates):")
    df1.union(df2).show()

    # --- union + distinct ---
    print("UNION + DISTINCT:")
    df1.union(df2).distinct().show()

    # --- unionByName (matches by column name, not position) ---
    df3 = spark.createDataFrame(
        [("Data", 3, "Charlie")],
        ["dept", "id", "name"]  # different column order!
    )
    print("unionByName (different column order):")
    df1.unionByName(df3).show()

    # --- dropDuplicates (by specific columns) ---
    print("dropDuplicates(['id']):")
    df1.union(df2).dropDuplicates(["id"]).show()

    # --- subtract (set difference) ---
    print("df1.subtract(df2) — rows in df1 not in df2:")
    df1.subtract(df2).show()

    # --- intersect ---
    print("df1.intersect(df2) — rows in both:")
    df1.intersect(df2).show()


# ═══════════════════════════════════════════════════════════════════════════════
# 13. PARTITION WRITING & BUCKETING
# ═══════════════════════════════════════════════════════════════════════════════

def demo_partition_writing(spark: SparkSession) -> None:
    print("\n" + "=" * 60)
    print("13. PARTITION WRITING")
    print("=" * 60)

    df = _build_employee_df(spark)

    output_dir = Path("_demo_spark_output")

    # --- Write partitioned by department ---
    df.write.mode("overwrite").partitionBy("dept").parquet(str(output_dir / "employees_by_dept"))
    print(f"Written partitioned Parquet to: {output_dir / 'employees_by_dept'}")

    # --- Read back and show partitions ---
    df_read = spark.read.parquet(str(output_dir / "employees_by_dept"))
    print("Partitions discovered:")
    df_read.select("dept").distinct().show()

    # --- Write with bucketing (for join optimization) ---
    df.write.mode("overwrite") \
       .bucketBy(4, "dept") \
       .sortBy("salary") \
       .saveAsTable("employees_bucketed")  # requires Hive support; may fail in local mode
    print("  (bucketing demo — requires Hive metastore; may be skipped in local mode)")

    # --- repartition / coalesce ---
    print(f"Original partitions: {df.rdd.getNumPartitions()}")
    df_repartitioned = df.repartition(2, "dept")
    print(f"After repartition(2, 'dept'): {df_repartitioned.rdd.getNumPartitions()}")
    df_coalesced = df.coalesce(1)
    print(f"After coalesce(1): {df_coalesced.rdd.getNumPartitions()}")

    # Cleanup
    import shutil
    if output_dir.exists():
        shutil.rmtree(output_dir)
    print("  (cleaned up demo output)")


# ═══════════════════════════════════════════════════════════════════════════════
# 14. COMMON ETL PATTERNS
# ═══════════════════════════════════════════════════════════════════════════════

def demo_etl_patterns(spark: SparkSession) -> None:
    print("\n" + "=" * 60)
    print("14. COMMON ETL PATTERNS")
    print("=" * 60)

    # --- SCD Type 2 (Slowly Changing Dimension) ---
    print("SCD Type 2 pattern:")
    current = spark.createDataFrame(
        [(1, "Alice", "Engineering", "2024-01-01", "9999-12-31", True),
         (2, "Bob",   "Data",        "2024-01-01", "9999-12-31", True)],
        ["emp_id", "name", "dept", "eff_start", "eff_end", "is_current"]
    )
    updates = spark.createDataFrame(
        [(1, "Alice", "Data")],  # Alice changed department
        ["emp_id", "name", "new_dept"]
    )
    print("Current dimension:")
    current.show()
    print("Updates:")
    updates.show()

    # Expire old records
    from pyspark.sql.functions import lit
    expired = current.alias("c").join(updates.alias("u"), "emp_id") \
        .filter(F.col("c.is_current") == True) \
        .select(
            F.col("c.emp_id"),
            F.col("c.name"),
            F.col("c.dept"),
            F.col("c.eff_start"),
            F.current_date().alias("eff_end"),
            F.lit(False).alias("is_current"),
        )
    print("Expired records:")
    expired.show()

    # --- Deduplication: keep latest record per key ---
    print("\nDeduplication (keep latest):")
    dupes = spark.createDataFrame(
        [(1, "Alice", "2024-01-01"),
         (1, "Alice", "2024-06-15"),  # duplicate, later date
         (2, "Bob",   "2024-03-10")],
        ["id", "name", "update_date"]
    )
    win_latest = Window.partitionBy("id").orderBy(F.col("update_date").desc())
    dupes.withColumn("rn", F.row_number().over(win_latest)) \
         .filter(F.col("rn") == 1) \
         .drop("rn") \
         .show()

    # --- Incremental load: new + updated records ---
    print("\nIncremental load (upsert pattern):")
    target = spark.createDataFrame(
        [(1, "Alice", 100), (2, "Bob", 200)],
        ["id", "name", "value"]
    )
    source = spark.createDataFrame(
        [(2, "Bob", 250), (3, "Charlie", 300)],  # Bob updated, Charlie new
        ["id", "name", "value"]
    )
    # Full outer + coalesce to pick source over target
    result = target.alias("t").join(source.alias("s"), "id", "full_outer") \
        .select(
            F.col("id"),
            F.coalesce(F.col("s.name"), F.col("t.name")).alias("name"),
            F.coalesce(F.col("s.value"), F.col("t.value")).alias("value"),
        )
    print("Upsert result (source wins on conflict):")
    result.show()


# ═══════════════════════════════════════════════════════════════════════════════
# 15. CACHE / PERSIST / CHECKPOINT
# ═══════════════════════════════════════════════════════════════════════════════

def demo_cache_persist(spark: SparkSession) -> None:
    print("\n" + "=" * 60)
    print("15. CACHE / PERSIST / CHECKPOINT")
    print("=" * 60)

    df = _build_employee_df(spark)

    # --- cache (default MEMORY_AND_DISK) ---
    df.cache()
    print(f"Storage level after cache(): {df.storageLevel}")

    # Force materialization
    count = df.count()
    print(f"Cached count: {count}")

    # --- persist with explicit storage level ---
    from pyspark import StorageLevel
    df.unpersist()
    df.persist(StorageLevel.MEMORY_ONLY)
    print(f"Storage level after persist(MEMORY_ONLY): {df.storageLevel}")
    df.unpersist()

    # --- Check if cached ---
    print(f"Is cached: {df.is_cached}")

    # --- Checkpoint (breaks lineage, saves to disk) ---
    spark.sparkContext.setCheckpointDir("_demo_checkpoint")
    try:
        df_checkpointed = df.checkpoint()
        print(f"Checkpointed: {df_checkpointed.count()} rows")
    except Exception as e:
        print(f"  (checkpoint demo: {e})")

    # Cleanup
    import shutil
    cp_dir = Path("_demo_checkpoint")
    if cp_dir.exists():
        shutil.rmtree(cp_dir)


# ═══════════════════════════════════════════════════════════════════════════════
# 16. BROADCAST VARIABLES & ACCUMULATORS
# ═══════════════════════════════════════════════════════════════════════════════

def demo_broadcast_accumulators(spark: SparkSession) -> None:
    print("\n" + "=" * 60)
    print("16. BROADCAST VARIABLES & ACCUMULATORS")
    print("=" * 60)

    # --- Broadcast variable (read-only shared lookup) ---
    dept_lookup = {"Engineering": "ENG", "Data": "DAT", "Product": "PRD",
                   "Marketing": "MKT", "Finance": "FIN"}
    broadcast_lookup = spark.sparkContext.broadcast(dept_lookup)

    df = _build_employee_df(spark)

    @F.udf(T.StringType())
    def map_dept_code(dept: str) -> str:
        return broadcast_lookup.value.get(dept, "UNK")

    df.withColumn("dept_code", map_dept_code("dept")) \
      .select("emp_name", "dept", "dept_code").show()

    # --- Accumulator (write-only counter across executors) ---
    high_earner_count = spark.sparkContext.accumulator(0)

    def count_high_earners(salary: float) -> None:
        if salary and salary > 120000:
            high_earner_count.add(1)

    # Accumulators are typically used inside foreach / foreachPartition
    for row in df.select("salary").collect():
        count_high_earners(row.salary)

    print(f"High earners (>120k): {high_earner_count.value}")


# ═══════════════════════════════════════════════════════════════════════════════
# 17. READING / WRITING DIFFERENT FORMATS
# ═══════════════════════════════════════════════════════════════════════════════

def demo_read_write_formats(spark: SparkSession) -> None:
    print("\n" + "=" * 60)
    print("17. READING / WRITING FORMATS")
    print("=" * 60)

    df = _build_employee_df(spark)
    base = Path("_demo_formats")

    # --- Parquet (columnar, default for Spark) ---
    parquet_path = str(base / "employees.parquet")
    df.write.mode("overwrite").parquet(parquet_path)
    df_parquet = spark.read.parquet(parquet_path)
    print(f"Parquet: {df_parquet.count()} rows")

    # --- CSV ---
    csv_path = str(base / "employees.csv")
    df.write.mode("overwrite").option("header", "true").csv(csv_path)
    df_csv = spark.read.option("header", "true").option("inferSchema", "true").csv(csv_path)
    print(f"CSV: {df_csv.count()} rows")

    # --- JSON ---
    json_path = str(base / "employees.json")
    df.write.mode("overwrite").json(json_path)
    df_json = spark.read.json(json_path)
    print(f"JSON: {df_json.count()} rows")

    # --- ORC ---
    orc_path = str(base / "employees.orc")
    df.write.mode("overwrite").orc(orc_path)
    df_orc = spark.read.orc(orc_path)
    print(f"ORC: {df_orc.count()} rows")

    # --- Delta Lake (conceptual — requires delta-spark package) ---
    print("Delta Lake: requires --packages io.delta:delta-spark_2.12:3.x.x")
    print("  df.write.mode('overwrite').format('delta').save(path)")
    print("  spark.read.format('delta').load(path)")

    # --- JDBC (conceptual) ---
    print("JDBC (conceptual):")
    print("  df.write.format('jdbc').option('url', 'jdbc:postgresql://...')")
    print("    .option('dbtable', 'employees').option('user', '...').save()")

    # Cleanup
    import shutil
    if base.exists():
        shutil.rmtree(base)
    print("  (cleaned up demo formats)")


# ═══════════════════════════════════════════════════════════════════════════════
# 18. PERFORMANCE TUNING — explain, partitioning, skew handling
# ═══════════════════════════════════════════════════════════════════════════════

def demo_performance(spark: SparkSession) -> None:
    print("\n" + "=" * 60)
    print("18. PERFORMANCE TUNING")
    print("=" * 60)

    df = _build_employee_df(spark)

    # --- explain (show physical plan) ---
    print("Physical plan for dept aggregation:")
    df.groupBy("dept").agg(F.avg("salary")).explain(extended=False)

    # --- spark.sql.shuffle.partitions ---
    print(f"spark.sql.shuffle.partitions = {spark.conf.get('spark.sql.shuffle.partitions')}")

    # --- Adaptive Query Execution (AQE) ---
    print(f"spark.sql.adaptive.enabled = {spark.conf.get('spark.sql.adaptive.enabled')}")

    # --- Salting for skew (conceptual) ---
    print("Skew handling with salting (conceptual):")
    print("  df.withColumn('salted_key', concat(col('key'), lit('_'), (rand() * 10).cast('int')))")
    print("  // Do join/aggregation on salted_key, then aggregate again on original key")

    # --- Predicate pushdown ---
    print("Predicate pushdown: filter before join, use partition filters in read")
    print("  spark.read.parquet(path).filter(col('date') >= '2024-01-01')")

    # --- Column pruning ---
    print("Column pruning: select only needed columns early")
    print("  df.select('id', 'name') rather than reading all columns then selecting")


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER — build the standard employee DataFrame
# ═══════════════════════════════════════════════════════════════════════════════

def _build_employee_df(spark: SparkSession) -> DataFrame:
    """Return a consistent employee DataFrame used across all demos.

    Uses string dates with explicit to_date() casting — the most portable
    pattern across Spark versions and avoids cloudpickle serialization issues
    with Python date objects in older Spark runtimes.
    """
    data = [
        (1, "Alice",   "Engineering", 120000.0, "2019-03-15"),
        (2, "Bob",     "Engineering", 110000.0, "2020-01-10"),
        (3, "Charlie", "Data",        130000.0, "2018-07-22"),
        (4, "Diana",   "Data",        125000.0, "2019-11-01"),
        (5, "Eve",     "Product",     105000.0, "2021-06-15"),
        (6, "Frank",   "Engineering", 115000.0, "2020-09-01"),
        (7, "Grace",   "Marketing",    95000.0, "2022-02-14"),
        (8, "Hank",    "Data",        140000.0, "2017-05-30"),
    ]
    schema = T.StructType([
        T.StructField("emp_id",    T.IntegerType(), False),
        T.StructField("emp_name",  T.StringType(),  False),
        T.StructField("dept",      T.StringType(),  False),
        T.StructField("salary",    T.DoubleType(),  False),
        T.StructField("hire_date", T.StringType(),  False),
    ])
    return spark.createDataFrame(data, schema=schema) \
        .withColumn("hire_date", F.to_date("hire_date", "yyyy-MM-dd"))


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    spark = build_spark()

    demos = [
        demo_create_dataframes,
        demo_select_filter,
        demo_aggregations,
        demo_joins,
        demo_window_functions,
        demo_udfs,
        demo_nulls,
        demo_dates,
        demo_strings,
        demo_pivot,
        demo_complex_types,
        demo_union_distinct,
        demo_partition_writing,
        demo_etl_patterns,
        demo_cache_persist,
        demo_broadcast_accumulators,
        demo_read_write_formats,
        demo_performance,
    ]

    for demo in demos:
        try:
            demo(spark)
        except Exception as e:
            print(f"  ERROR in {demo.__name__}: {e}")

    print("\n" + "=" * 60)
    print("All PySpark demos complete.")
    print("=" * 60)

    spark.stop()


if __name__ == "__main__":
    main()
