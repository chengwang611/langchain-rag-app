# Sample Questions — PySpark Setup Guide for macOS

> How to run `spark-basic.py` and other PySpark scripts on your Mac without
> `PYTHON_VERSION_MISMATCH` errors.

---

## The Problem

On macOS, you likely have **multiple Python versions** installed:

| Python | Location | Version |
|---|---|---|
| Homebrew | `/opt/homebrew/bin/python3` | 3.13 |
| Homebrew | `/opt/homebrew/bin/python3.11` | 3.11.10 |
| macOS Framework | `/Library/Frameworks/Python.framework/Versions/3.11/bin/python3` | 3.11.9 |
| macOS Framework | `/Library/Frameworks/Python.framework/Versions/3.9/bin/python3` | 3.9.20 |

PySpark spawns **separate worker processes** for distributed execution. When the driver Python (3.11) differs from the worker Python (3.9), you get:

```
pyspark.errors.exceptions.base.PySparkRuntimeError: [PYTHON_VERSION_MISMATCH]
Python in worker has different version (3, 9) than that in driver 3.11
```

---

## Quick Fix — Run with the Right Python

Find which Python has PySpark installed:

```bash
/Library/Frameworks/Python.framework/Versions/3.11/bin/python3 -c "import pyspark; print(pyspark.__version__)"
```

Then run the script with explicit `PYSPARK_PYTHON`:

```bash
PYSPARK_PYTHON=/Library/Frameworks/Python.framework/Versions/3.11/bin/python3 \
PYSPARK_DRIVER_PYTHON=/Library/Frameworks/Python.framework/Versions/3.11/bin/python3 \
/Library/Frameworks/Python.framework/Versions/3.11/bin/python3 src/sample-questions/spark-basic.py
```

---

## Permanent Fix — Set Environment Variables

Add these to your `~/.zshrc`:

```bash
# Point to the Python that has PySpark installed
export PYSPARK_PYTHON=/Library/Frameworks/Python.framework/Versions/3.11/bin/python3
export PYSPARK_DRIVER_PYTHON=/Library/Frameworks/Python.framework/Versions/3.11/bin/python3
```

Then reload:

```bash
source ~/.zshrc
python3 src/sample-questions/spark-basic.py
```

---

## Verify It Works

```bash
# Check PySpark version
/Library/Frameworks/Python.framework/Versions/3.11/bin/python3 -c "
import pyspark
from pyspark.sql import SparkSession
spark = SparkSession.builder.appName('test').master('local[*]').getOrCreate()
df = spark.range(5)
print(f'PySpark {pyspark.__version__} OK — count={df.count()}')
spark.stop()
"
```

Expected output:

```
PySpark 3.5.0 OK — count=5
```

---

## How the Embedding Pipeline Handles This

The project's [`embedding_process/main.py`](../src/capital_market_risk_review/embedding_process/main.py:51-63) already has a robust `_resolve_python_exec()` function that checks in order:

1. `EMBEDDING_PROCESS_PYTHON_EXEC` env var (explicit override)
2. `PYSPARK_PYTHON` env var
3. `sys.executable` (current interpreter)

This is why the embedding pipeline works in Docker (single consistent Python) but the sample script fails on your Mac (multiple Python versions).

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `PYTHON_VERSION_MISMATCH` | Driver and worker use different Python | Set `PYSPARK_PYTHON` |
| `No module named 'pyspark'` | PySpark not installed for this Python | `pip3 install pyspark` |
| `Java not found` | No JDK installed | `brew install openjdk@17` |
| `SparkSession` hangs | Port conflict or DNS issue | Set `SPARK_LOCAL_IP=127.0.0.1` |
