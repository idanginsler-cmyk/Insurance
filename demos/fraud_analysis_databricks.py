# Databricks notebook source
# MAGIC %md
# MAGIC # 🔍 ניתוח הונאות ביטוח בריאות
# MAGIC
# MAGIC ניתוח CSV תביעות לזיהוי דפוסי הונאה.
# MAGIC
# MAGIC **מקור נתונים:** קובץ CSV שהעלית
# MAGIC **פלט:** דשבורד עם התראות, דירוגים, ותובנות

# COMMAND ----------

# MAGIC %md
# MAGIC ## שלב 1: טעינת הקובץ

# COMMAND ----------

# ↓↓↓ אחרי שהעלית את ה-CSV, עדכן את הנתיב כאן ↓↓↓
file_path = "/FileStore/tables/claims_2025.csv"

df = spark.read.csv(file_path, header=True, inferSchema=True)
print(f"נטענו {df.count():,} תביעות")
display(df.limit(10))

# COMMAND ----------

# MAGIC %md
# MAGIC ## שלב 2: סטטיסטיקות בסיסיות

# COMMAND ----------

from pyspark.sql.functions import count, sum as _sum, avg, countDistinct, col

stats = df.agg(
    count("*").alias("total_claims"),
    _sum("amount_claimed").alias("total_claimed"),
    _sum("amount_paid").alias("total_paid"),
    countDistinct("insured_id").alias("unique_insured"),
    countDistinct("provider").alias("unique_providers")
)
display(stats)

# COMMAND ----------

# MAGIC %md
# MAGIC ## שלב 3: מבוטחים עם תדירות חריגה

# COMMAND ----------

from pyspark.sql.functions import desc

by_insured = df.groupBy("insured_name", "insured_id").agg(
    count("*").alias("claims_count"),
    _sum("amount_claimed").alias("total_amount"),
    countDistinct("provider").alias("providers_used")
).orderBy(desc("claims_count"))

# Top 20 מבוטחים לפי תדירות
print("🔴 20 המבוטחים עם הכי הרבה תביעות:")
display(by_insured.limit(20))

# COMMAND ----------

# MAGIC %md
# MAGIC ## שלב 4: ניתוח נותני שירות

# COMMAND ----------

by_provider = df.groupBy("provider").agg(
    count("*").alias("claims"),
    avg("amount_claimed").alias("avg_amount"),
    countDistinct("insured_id").alias("unique_insured"),
    countDistinct("employer").alias("unique_employers")
).orderBy(desc("claims"))

print("🏥 נותני שירות - מדורגים לפי נפח:")
display(by_provider)

# COMMAND ----------

# MAGIC %md
# MAGIC ## שלב 5: ריכוז מעסיקים חשוד

# COMMAND ----------

from pyspark.sql.functions import when, lit

# לכל נותן שירות - מעסיק דומיננטי
emp_concentration = df.groupBy("provider", "employer").count()\
    .orderBy("provider", desc("count"))

# תביעות סך הכל לכל נותן שירות
total_per_prov = df.groupBy("provider").count().withColumnRenamed("count", "total")

# אחוז המעסיק הדומיננטי
joined = emp_concentration.join(total_per_prov, "provider")
joined = joined.withColumn("pct", (col("count") / col("total") * 100).cast("int"))

# רק ריכוזים חשודים (>30%)
suspicious = joined.filter(col("pct") > 30).orderBy(desc("pct"))
print("⚠️ ריכוזי מעסיקים חשודים (>30%):")
display(suspicious)

# COMMAND ----------

# MAGIC %md
# MAGIC ## שלב 6: תביעות מפוליסות חדשות (תוך 60 יום)

# COMMAND ----------

from pyspark.sql.functions import datediff, to_date

df_dates = df.withColumn("days_since_start",
    datediff(to_date("date"), to_date("policy_start"))
)

quick_claims = df_dates.filter(
    (col("days_since_start") <= 60) & (col("days_since_start") >= 0)
)
print(f"🏃 תביעות תוך 60 יום מפוליסה חדשה: {quick_claims.count()}")
display(quick_claims.orderBy("days_since_start").limit(30))

# COMMAND ----------

# MAGIC %md
# MAGIC ## שלב 7: סכומים עגולים (חשוד)

# COMMAND ----------

round_claims = df.filter(
    (col("amount_claimed") % 500 == 0) & (col("amount_claimed") >= 500)
)
print(f"💰 תביעות בסכומים עגולים (כפולות 500): {round_claims.count()}")
display(round_claims.groupBy("provider").count().orderBy(desc("count")))

# COMMAND ----------

# MAGIC %md
# MAGIC ## שלב 8: אשכולות משפחתיים

# COMMAND ----------

from pyspark.sql.functions import split, element_at

# חילוץ שם משפחה
df_fam = df.withColumn("last_name",
    element_at(split(col("insured_name"), " "), -1)
)

# קבוצות לפי: שם משפחה + עיר + נותן שירות
family_clusters = df_fam.groupBy("last_name", "city", "provider").agg(
    countDistinct("insured_id").alias("unique_members"),
    count("*").alias("total_claims"),
    _sum("amount_claimed").alias("total_amount")
).filter(
    (col("unique_members") >= 3) & (col("total_claims") >= 8)
).orderBy(desc("total_claims"))

print("👥 אשכולות משפחתיים חשודים:")
display(family_clusters)

# COMMAND ----------

# MAGIC %md
# MAGIC ## שלב 9: התפלגות חודשית - זיהוי ריצת סוף שנה

# COMMAND ----------

from pyspark.sql.functions import month

monthly = df.withColumn("month", month("date")).groupBy("month").agg(
    count("*").alias("claims"),
    _sum("amount_claimed").alias("total_amount")
).orderBy("month")

print("📅 התפלגות חודשית:")
display(monthly)

# COMMAND ----------

# MAGIC %md
# MAGIC ## שלב 10: התפלגות כיסויים

# COMMAND ----------

coverage_dist = df.groupBy("coverage").agg(
    count("*").alias("claims"),
    avg("amount_claimed").alias("avg"),
    _sum("amount_claimed").alias("total")
).orderBy(desc("claims"))

print("📋 התפלגות כיסויים:")
display(coverage_dist)

# COMMAND ----------

# MAGIC %md
# MAGIC ## שלב 11: ציון סיכון למבוטחים

# COMMAND ----------

# חישוב ציון סיכון מצטבר
avg_claims_per_person = df.count() / df.select("insured_id").distinct().count()

risk_scores = by_insured.withColumn("frequency_score",
    when(col("claims_count") > avg_claims_per_person * 10, 40)
    .when(col("claims_count") > avg_claims_per_person * 5, 25)
    .when(col("claims_count") > avg_claims_per_person * 3, 15)
    .otherwise(0)
).withColumn("single_provider_score",
    when(col("providers_used") == 1, 20)
    .when(col("providers_used") == 2, 10)
    .otherwise(0)
).withColumn("risk_score",
    col("frequency_score") + col("single_provider_score")
).orderBy(desc("risk_score"))

print("🎯 מבוטחים עם ציון סיכון גבוה:")
display(risk_scores.filter(col("risk_score") > 20).limit(30))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 📊 סיכום - כל ההתראות

# COMMAND ----------

print("="*60)
print("📋 סיכום ניתוח הונאות")
print("="*60)
print(f"\n📊 סה\"כ תביעות: {df.count():,}")
print(f"📊 מבוטחים ייחודיים: {df.select('insured_id').distinct().count()}")
print(f"\n🔴 התראות:")
print(f"  • מבוטחים עם ציון סיכון >20: {risk_scores.filter(col('risk_score') > 20).count()}")
print(f"  • אשכולות משפחתיים חשודים: {family_clusters.count()}")
print(f"  • ריכוזי מעסיקים חשודים: {suspicious.count()}")
print(f"  • תביעות מפוליסות חדשות (60 יום): {quick_claims.count()}")
print(f"  • תביעות בסכומים עגולים: {round_claims.count()}")
