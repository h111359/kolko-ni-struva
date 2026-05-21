# Coding Scala Convention

**Scope:** Normative  
**Applies to:** All Scala source files (`.scala`) created or edited by the AI Automation Agent during any `implement` workflow run, including application code, test code, configuration classes, and Spark job files.  
**Extends:** `coding-general-convention.md` — all rules defined there MUST be applied in addition to the rules below.

---

## 1. Purpose

This convention defines Scala-specific commenting and code-quality rules for AI-generated Scala code. It ensures that classes, objects, traits, methods, and Spark transformations are self-documented using idiomatic ScalaDoc comments consistent with Scala community practices.

---

## 2. Scope & Normative Language

This convention applies to:

- All `.scala` files created or modified by the AI Automation Agent.
- Scala application code, Spark job definitions, and library code.
- Test code (ScalaTest, MUnit, Specs2).

Out of scope:
- Auto-generated Scala files (e.g., generated from Avro schemas, Protobuf, or Play routes) where the AI does not write substantive logic.
- `build.sbt` and `project/*.scala` build files — apply best-effort only.

Normative keywords **MUST**, **MUST NOT**, **SHALL**, **SHOULD**, and **MAY** are interpreted per BCP 14 (RFC 2119 / RFC 8174).

---

## 3. File-Level Header

Every Scala file MUST begin with a file-level comment block using `//` that contains:

- The file name and a one-sentence description of the file's purpose.
- The package it belongs to and the primary class or object it defines.

Example:

```scala
// SalesAggregationJob.scala: Spark job for aggregating daily sales transactions by region.
// Package: com.example.analytics.jobs
// Defines: SalesAggregationJob (Spark batch job entry point)
```

---

## 4. ScalaDoc Comments

Every public class, object, trait, case class, and def MUST have a ScalaDoc comment (`/** ... */`) immediately above its definition.

The ScalaDoc block MUST include:

- A brief description of the class/method's purpose or contract.
- `@param` tags for every type and value parameter.
- `@return` tag for every non-Unit method.
- `@throws` tag for any explicitly thrown exceptions.
- `@tparam` tags for type parameters when their constraint or semantics require explanation.

Example:

```scala
/**
 * Aggregates daily sales transactions by region and product category.
 *
 * @param spark    The active SparkSession used to execute the job.
 * @param inputPath  HDFS or S3 path to the input Parquet dataset.
 * @param outputPath HDFS or S3 path where the aggregated results are written.
 * @return The number of output partitions written.
 * @throws IllegalArgumentException if inputPath or outputPath is empty.
 */
def run(spark: SparkSession, inputPath: String, outputPath: String): Int =
```

Companion objects and case classes SHOULD have a ScalaDoc comment describing their role.

---

## 5. Spark Transformation Comments

Every Spark DataFrame transformation chain MUST be annotated with a preceding `//` comment that:

- States the purpose of the transformation step (what the resulting DataFrame represents).
- Explains any non-obvious joins, window functions, or filter conditions.

Example:

```scala
// Compute 7-day rolling average of daily sales per region,
// using a window ordered by date with a 6-row preceding frame.
val rollingAvgDf = salesDf
  .withColumn(
    "rolling_avg_sales",
    avg("daily_sales").over(windowSpec)
  )
```

---

## 6. Implicit and Type Class Comments

Every `implicit` value, class, or conversion MUST have a ScalaDoc comment explaining:

- What the implicit provides (the capability or type conversion).
- Where it is expected to be in scope and how it is resolved.

---

## 7. Pattern Matching Comments

Complex `match` expressions MUST be preceded by a `//` comment describing the discriminant and intended cases.

Each `case` branch in a non-trivial match SHOULD have an inline `//` comment explaining the condition it handles.

---

## 8. Constants and Configuration Values

Companion object constants and `val` definitions at object scope MUST have an inline `//` comment or ScalaDoc describing their meaning and acceptable value range.

---

## 9. Code Quality Rules

- Methods MUST NOT exceed 40 lines of executable code; decompose into named helper methods with ScalaDoc.
- `null` references are PROHIBITED; use `Option[T]` with a comment explaining the optional semantics.
- `asInstanceOf` casts MUST be accompanied by a comment explaining why the cast is safe and why the type cannot be enforced at compile time.
- Mutable `var` declarations MUST be commented with the reason mutability is necessary; prefer `val` and immutable patterns.
- Anonymous function literals used as arguments MUST be assigned to a named `val` with a comment if the logic is non-trivial.
