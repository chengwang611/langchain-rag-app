"""
============================================================================
Data Engineer Python Interview — Core Concepts Demo
============================================================================
Covers: list, tuple, set, dict, comprehensions, loops, functions,
        lambda, map/filter/reduce, generators, sorting, error handling,
        file I/O, collections, itertools, and common interview patterns.

Run: python python-basic.py
============================================================================
"""

from __future__ import annotations

import json
import os
import sys
from collections import Counter, OrderedDict, defaultdict, deque, namedtuple
from functools import reduce
from itertools import chain, combinations, groupby, islice, permutations, product
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Set, Tuple


# ═══════════════════════════════════════════════════════════════════════════════
# 1. LISTS — creation, slicing, methods
# ═══════════════════════════════════════════════════════════════════════════════

def demo_lists() -> None:
    print("=" * 60)
    print("1. LISTS")
    print("=" * 60)

    # Creation
    nums: List[int] = [3, 1, 4, 1, 5, 9, 2, 6, 5, 3]
    print(f"Original:          {nums}")

    # Slicing  [start:stop:step]
    print(f"nums[2:5]:         {nums[2:5]}")       # [4, 1, 5]
    print(f"nums[:3]:          {nums[:3]}")        # [3, 1, 4]
    print(f"nums[::2]:         {nums[::2]}")       # [3, 4, 5, 2, 5]
    print(f"nums[::-1]:        {nums[::-1]}")      # reverse

    # Methods
    nums.append(7)
    print(f"append(7):         {nums}")

    nums.extend([8, 9])
    print(f"extend([8,9]):     {nums}")

    nums.insert(0, 0)
    print(f"insert(0,0):       {nums}")

    popped = nums.pop()
    print(f"pop():             {popped} --> {nums}")

    nums.remove(5)  # removes first occurrence
    print(f"remove(5):         {nums}")

    idx = nums.index(9)
    print(f"index(9):          {idx}")

    count_1 = nums.count(1)
    print(f"count(1):          {count_1}")

    nums.sort(reverse=True)
    print(f"sort(reverse=True): {nums}")

    # List comprehension
    squares = [x ** 2 for x in range(1, 6)]
    print(f"[x**2 for x in 1..5]: {squares}")

    # Filter with comprehension
    evens = [x for x in range(10) if x % 2 == 0]
    print(f"evens < 10:         {evens}")

    # Nested comprehension (flatten)
    matrix = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    flat = [x for row in matrix for x in row]
    print(f"flatten 3x3:        {flat}")

    # zip two lists
    names = ["Alice", "Bob", "Charlie"]
    scores = [85, 92, 78]
    paired = list(zip(names, scores))
    print(f"zip(names,scores):  {paired}")

    # enumerate
    for i, name in enumerate(names, start=1):
        print(f"  #{i}: {name}")


# ═══════════════════════════════════════════════════════════════════════════════
# 2. TUPLES — immutable, unpacking, namedtuple
# ═══════════════════════════════════════════════════════════════════════════════

def demo_tuples() -> None:
    print("\n" + "=" * 60)
    print("2. TUPLES")
    print("=" * 60)

    # Creation
    point: Tuple[int, int, int] = (10, 20, 30)
    print(f"point:              {point}")

    # Unpacking
    x, y, z = point
    print(f"unpack:             x={x}, y={y}, z={z}")

    # Swap in one line (uses tuple unpacking)
    a, b = 5, 10
    a, b = b, a
    print(f"swap a=5,b=10 -->    a={a}, b={b}")

    # Single-element tuple (trailing comma required)
    single: Tuple[int] = (42,)
    print(f"single-element:     {single}  type={type(single).__name__}")

    # namedtuple — lightweight class
    Employee = namedtuple("Employee", ["name", "dept", "salary"])
    e = Employee("Alice", "Engineering", 120000)
    print(f"namedtuple:         {e.name} | {e.dept} | ${e.salary:,}")

    # _asdict()
    print(f"_asdict():          {e._asdict()}")

    # tuple as dict key (immutable --> hashable)
    cache: Dict[Tuple[int, int], str] = {(0, 0): "origin", (1, 0): "right"}
    print(f"tuple as key:       {cache[(1, 0)]}")


# ═══════════════════════════════════════════════════════════════════════════════
# 3. SETS — unique, operations, set comprehension
# ═══════════════════════════════════════════════════════════════════════════════

def demo_sets() -> None:
    print("\n" + "=" * 60)
    print("3. SETS")
    print("=" * 60)

    a: Set[int] = {1, 2, 3, 4, 5}
    b: Set[int] = {4, 5, 6, 7, 8}
    print(f"a:                  {a}")
    print(f"b:                  {b}")

    # Set operations
    print(f"union (a | b):      {a | b}")
    print(f"intersection (a&b): {a & b}")
    print(f"difference (a - b): {a - b}")
    print(f"symmetric_diff:     {a ^ b}")

    # Deduplicate a list
    dupes = [1, 2, 2, 3, 3, 3, 4]
    unique = list(set(dupes))
    print(f"deduplicate list:   {dupes} --> {unique}")

    # Set comprehension
    word = "mississippi"
    unique_chars = {c for c in word}
    print(f"unique chars in '{word}': {sorted(unique_chars)}")

    # Membership test (O(1) average)
    print(f"3 in a:             {3 in a}")
    print(f"99 in a:            {99 in a}")

    # add / remove / discard
    s: Set[int] = {1, 2}
    s.add(3)
    s.discard(99)  # no error if missing
    print(f"add/discard:        {s}")


# ═══════════════════════════════════════════════════════════════════════════════
# 4. DICTIONARIES — creation, methods, comprehension, defaultdict, Counter
# ═══════════════════════════════════════════════════════════════════════════════

def demo_dicts() -> None:
    print("\n" + "=" * 60)
    print("4. DICTIONARIES")
    print("=" * 60)

    # Creation
    emp: Dict[str, Any] = {
        "name": "Alice",
        "dept": "Engineering",
        "salary": 120000,
        "skills": ["Python", "SQL", "Spark"],
    }
    print(f"emp:                {emp}")

    # Access with default
    print(f"emp.get('name'):    {emp.get('name')}")
    print(f"emp.get('bonus',0): {emp.get('bonus', 0)}")

    # keys / values / items
    print(f"keys:               {list(emp.keys())}")
    print(f"values:             {list(emp.values())}")

    # Dict comprehension
    squares_dict = {x: x ** 2 for x in range(1, 6)}
    print(f"dict comprehension:  {squares_dict}")

    # Merge dicts (Python 3.9+)
    d1 = {"a": 1, "b": 2}
    d2 = {"b": 99, "c": 3}
    merged = d1 | d2  # d2 wins on conflict
    print(f"merge d1 | d2:      {merged}")

    # defaultdict — auto-initialize missing keys
    from collections import defaultdict
    groups: defaultdict[str, List[int]] = defaultdict(list)
    for word in ["apple", "banana", "apricot", "blueberry", "avocado"]:
        groups[word[0]].append(word)
    print(f"defaultdict group:  {dict(groups)}")

    # Counter — frequency counting
    from collections import Counter
    text = "abracadabra"
    freq = Counter(text)
    print(f"Counter('{text}'):  {freq}")
    print(f"most_common(2):     {freq.most_common(2)}")

    # OrderedDict (Python 3.7+ dicts are insertion-ordered, but OrderedDict
    # still useful for equality comparisons that consider order)
    od = OrderedDict()
    od["z"] = 1
    od["a"] = 2
    od["m"] = 3
    print(f"OrderedDict:        {od}")


# ═══════════════════════════════════════════════════════════════════════════════
# 5. LOOPS — for, while, break, continue, else, enumerate, zip
# ═══════════════════════════════════════════════════════════════════════════════

def demo_loops() -> None:
    print("\n" + "=" * 60)
    print("5. LOOPS")
    print("=" * 60)

    # for-else: else runs if loop completes without break
    print("for-else (find prime):")
    for n in range(2, 20):
        for d in range(2, int(n ** 0.5) + 1):
            if n % d == 0:
                break
        else:
            print(f"  {n} is prime")

    # while with break/continue
    print("while loop:")
    i = 0
    while i < 5:
        i += 1
        if i == 3:
            continue  # skip 3
        print(f"  i={i}")

    # Iterate dict
    print("iterate dict:")
    d = {"a": 1, "b": 2, "c": 3}
    for k, v in d.items():
        print(f"  {k} --> {v}")

    # reversed iteration
    print("reversed:")
    for x in reversed(range(1, 6)):
        print(f"  {x}", end=" ")
    print()


# ═══════════════════════════════════════════════════════════════════════════════
# 6. FUNCTIONS — args, kwargs, type hints, default mutability trap
# ═══════════════════════════════════════════════════════════════════════════════

def demo_functions() -> None:
    print("\n" + "=" * 60)
    print("6. FUNCTIONS")
    print("=" * 60)

    # *args (variable positional) and **kwargs (variable keyword)
    def log_all(*args: Any, **kwargs: Any) -> None:
        print(f"  args:   {args}")
        print(f"  kwargs: {kwargs}")

    log_all(1, 2, 3, name="Alice", dept="Engineering")

    # Default argument trap: mutable defaults are shared across calls!
    def bad_append(item: int, target: List[int] = []) -> List[int]:
        target.append(item)
        return target

    print(f"  bad_append(1): {bad_append(1)}")  # [1]
    print(f"  bad_append(2): {bad_append(2)}")  # [1, 2] ← SURPRISE!

    # Correct pattern: use None and create new list inside
    def good_append(item: int, target: Optional[List[int]] = None) -> List[int]:
        if target is None:
            target = []
        target.append(item)
        return target

    print(f"  good_append(1): {good_append(1)}")  # [1]
    print(f"  good_append(2): {good_append(2)}")  # [2] ← correct

    # Type hints with return type
    def add(a: int, b: int) -> int:
        return a + b

    print(f"  add(3, 4): {add(3, 4)}")


# ═══════════════════════════════════════════════════════════════════════════════
# 7. LAMBDA, MAP, FILTER, REDUCE
# ═══════════════════════════════════════════════════════════════════════════════

def demo_lambda_map_filter_reduce() -> None:
    print("\n" + "=" * 60)
    print("7. LAMBDA / MAP / FILTER / REDUCE")
    print("=" * 60)

    nums = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

    # lambda — anonymous inline function
    square = lambda x: x ** 2
    print(f"lambda square(5):   {square(5)}")

    # map — apply function to every element
    doubled = list(map(lambda x: x * 2, nums))
    print(f"map(x*2):           {doubled}")

    # filter — keep elements where predicate is True
    evens = list(filter(lambda x: x % 2 == 0, nums))
    print(f"filter(even):       {evens}")

    # reduce — cumulative operation (needs functools.reduce)
    from functools import reduce
    total = reduce(lambda acc, x: acc + x, nums)
    product_val = reduce(lambda acc, x: acc * x, nums)
    print(f"reduce(sum):        {total}")
    print(f"reduce(product):    {product_val}")

    # sorted with key
    words = ["banana", "apple", "Cherry", "date"]
    by_len = sorted(words, key=lambda w: len(w))
    by_lower = sorted(words, key=str.lower)
    print(f"sorted by len:      {by_len}")
    print(f"sorted case-insens: {by_lower}")

    # max/min with key
    longest = max(words, key=len)
    print(f"longest word:       {longest}")


# ═══════════════════════════════════════════════════════════════════════════════
# 8. GENERATORS — yield, generator expressions, memory efficiency
# ═══════════════════════════════════════════════════════════════════════════════

def demo_generators() -> None:
    print("\n" + "=" * 60)
    print("8. GENERATORS")
    print("=" * 60)

    # Generator function (yield instead of return)
    def fibonacci(n: int) -> Generator[int, None, None]:
        a, b = 0, 1
        for _ in range(n):
            yield a
            a, b = b, a + b

    print("fibonacci(10):")
    for num in fibonacci(10):
        print(f"  {num}", end="")
    print()

    # Generator expression (like list comprehension but lazy)
    squares_gen = (x ** 2 for x in range(1, 6))
    print(f"genexpr type:       {type(squares_gen).__name__}")
    print(f"genexpr --> list:    {list(squares_gen)}")

    # Memory comparison
    import sys
    big_list = [x for x in range(1_000_000)]
    big_gen = (x for x in range(1_000_000))
    print(f"list 1M size:       {sys.getsizeof(big_list):,} bytes")
    print(f"gen  1M size:       {sys.getsizeof(big_gen):,} bytes")

    # islice — slice a generator
    from itertools import islice
    first_five = list(islice(fibonacci(100), 5))
    print(f"islice fib(5):      {first_five}")


# ═══════════════════════════════════════════════════════════════════════════════
# 9. ERROR HANDLING — try/except/else/finally, custom exceptions
# ═══════════════════════════════════════════════════════════════════════════════

def demo_error_handling() -> None:
    print("\n" + "=" * 60)
    print("9. ERROR HANDLING")
    print("=" * 60)

    # Basic try/except
    try:
        result = 10 / 0
    except ZeroDivisionError as e:
        print(f"  caught: {type(e).__name__}: {e}")

    # Multiple exceptions
    for val in ["123", "abc", "0"]:
        try:
            print(f"  100 / {val} = {100 / int(val):.2f}")
        except ValueError:
            print(f"  '{val}' is not a valid integer")
        except ZeroDivisionError:
            print(f"  division by zero for '{val}'")

    # try/except/else/finally
    print("  try/except/else/finally:")
    try:
        num = int("42")
    except ValueError:
        print("    except: bad value")
    else:
        print(f"    else: conversion OK --> {num}")  # runs only if no exception
    finally:
        print("    finally: always runs")

    # Custom exception
    class DataQualityError(Exception):
        """Raised when data fails quality checks."""
        pass

    def validate_positive(n: int) -> int:
        if n <= 0:
            raise DataQualityError(f"Expected positive, got {n}")
        return n

    try:
        validate_positive(-5)
    except DataQualityError as e:
        print(f"  custom exception: {e}")

    # Context manager (with statement)
    print("  context manager (with):")
    with open(os.devnull, "w") as f:
        f.write("nothing")
    print("    file auto-closed")


# ═══════════════════════════════════════════════════════════════════════════════
# 10. FILE I/O — read, write, JSON, CSV, Path
# ═══════════════════════════════════════════════════════════════════════════════

def demo_file_io() -> None:
    print("\n" + "=" * 60)
    print("10. FILE I/O")
    print("=" * 60)

    tmp = Path("_demo_temp.txt")

    # Write
    tmp.write_text("line1\nline2\nline3\n", encoding="utf-8")
    print(f"  wrote: {tmp}")

    # Read entire file
    content = tmp.read_text(encoding="utf-8")
    print(f"  read all: {content.strip().split()}")

    # Read lines
    with tmp.open("r", encoding="utf-8") as f:
        lines = [line.strip() for line in f]
    print(f"  readlines: {lines}")

    # JSON
    data = {"employees": [{"name": "Alice", "salary": 120000}]}
    json_str = json.dumps(data, indent=2)
    print(f"  json dumps:\n{json_str}")
    parsed = json.loads(json_str)
    print(f"  json loads: {parsed['employees'][0]['name']}")

    # Path operations
    print(f"  Path.name:     {tmp.name}")
    print(f"  Path.suffix:   {tmp.suffix}")
    print(f"  Path.parent:   {tmp.parent}")
    print(f"  Path.exists(): {tmp.exists()}")

    # Cleanup
    tmp.unlink()
    print(f"  deleted: {tmp}")


# ═══════════════════════════════════════════════════════════════════════════════
# 11. COLLECTIONS MODULE — deque, Counter, defaultdict, ChainMap
# ═══════════════════════════════════════════════════════════════════════════════

def demo_collections() -> None:
    print("\n" + "=" * 60)
    print("11. COLLECTIONS")
    print("=" * 60)

    # deque — fast append/pop from both ends
    dq: deque[str] = deque(["a", "b", "c"])
    dq.append("d")
    dq.appendleft("z")
    print(f"deque:              {dq}")
    print(f"dq.pop():           {dq.pop()}")
    print(f"dq.popleft():       {dq.popleft()}")

    # Counter arithmetic
    c1 = Counter("abracadabra")
    c2 = Counter("alakazam")
    print(f"Counter add:        {c1 + c2}")
    print(f"Counter subtract:   {c1 - c2}")
    print(f"Counter intersect:  {c1 & c2}")

    # defaultdict with int (counter pattern)
    dd: defaultdict[str, int] = defaultdict(int)
    for word in ["a", "b", "a", "c", "b", "a"]:
        dd[word] += 1
    print(f"defaultdict(int):   {dict(dd)}")


# ═══════════════════════════════════════════════════════════════════════════════
# 12. ITERTOOLS — chain, combinations, permutations, product, groupby
# ═══════════════════════════════════════════════════════════════════════════════

def demo_itertools() -> None:
    print("\n" + "=" * 60)
    print("12. ITERTOOLS")
    print("=" * 60)

    # chain — flatten iterables
    chained = list(chain([1, 2], [3, 4], [5, 6]))
    print(f"chain:              {chained}")

    # combinations (order doesn't matter)
    comb = list(combinations("ABC", 2))
    print(f"combinations(3,2):  {comb}")

    # permutations (order matters)
    perm = list(permutations("AB", 2))
    print(f"permutations(2,2):  {perm}")

    # product (cartesian product)
    prod = list(product("AB", "12"))
    print(f"product(AB,12):     {prod}")

    # groupby — group consecutive elements by key
    data = [("A", 1), ("A", 2), ("B", 3), ("B", 4), ("A", 5)]
    grouped = {k: list(v) for k, v in groupby(data, key=lambda x: x[0])}
    print(f"groupby:            {grouped}")

    # islice
    from itertools import islice
    sliced = list(islice(range(100), 10, 20))
    print(f"islice(10,20):      {sliced}")


# ═══════════════════════════════════════════════════════════════════════════════
# 13. COMMON INTERVIEW PATTERNS
# ═══════════════════════════════════════════════════════════════════════════════

def demo_interview_patterns() -> None:
    print("\n" + "=" * 60)
    print("13. COMMON INTERVIEW PATTERNS")
    print("=" * 60)

    # --- FizzBuzz ---
    print("FizzBuzz:")
    for i in range(1, 16):
        if i % 15 == 0:
            print("  FizzBuzz", end="")
        elif i % 3 == 0:
            print("  Fizz", end="")
        elif i % 5 == 0:
            print("  Buzz", end="")
        else:
            print(f"  {i}", end="")
    print()

    # --- Palindrome check ---
    def is_palindrome(s: str) -> bool:
        cleaned = "".join(c.lower() for c in s if c.isalnum())
        return cleaned == cleaned[::-1]

    print(f"is_palindrome('A man a plan a canal Panama'): {is_palindrome('A man a plan a canal Panama')}")

    # --- Two-sum (find indices of two numbers that add to target) ---
    def two_sum(nums: List[int], target: int) -> Optional[Tuple[int, int]]:
        seen: Dict[int, int] = {}
        for i, n in enumerate(nums):
            complement = target - n
            if complement in seen:
                return (seen[complement], i)
            seen[n] = i
        return None

    print(f"two_sum([2,7,11,15], 9): {two_sum([2, 7, 11, 15], 9)}")

    # --- Word count (most frequent word) ---
    sentence = "the quick brown fox jumps over the lazy dog the fox"
    word_counts = Counter(sentence.split())
    print(f"most common word:    {word_counts.most_common(1)[0]}")

    # --- Flatten nested list ---
    def flatten(nested: List[Any]) -> List[Any]:
        result: List[Any] = []
        for item in nested:
            if isinstance(item, list):
                result.extend(flatten(item))
            else:
                result.append(item)
        return result

    nested = [1, [2, [3, 4], 5], 6]
    print(f"flatten {nested}: {flatten(nested)}")

    # --- Group anagrams ---
    words = ["eat", "tea", "tan", "ate", "nat", "bat"]
    anagram_groups: defaultdict[str, List[str]] = defaultdict(list)
    for w in words:
        key = "".join(sorted(w))
        anagram_groups[key].append(w)
    print(f"anagram groups:      {list(anagram_groups.values())}")

    # --- Find missing number (0..n with one missing) ---
    nums = [0, 1, 2, 4, 5]
    n = len(nums)
    expected_sum = n * (n + 1) // 2
    actual_sum = sum(nums)
    print(f"missing number in {nums}: {expected_sum - actual_sum}")

    # --- Binary search ---
    def binary_search(arr: List[int], target: int) -> int:
        lo, hi = 0, len(arr) - 1
        while lo <= hi:
            mid = (lo + hi) // 2
            if arr[mid] == target:
                return mid
            elif arr[mid] < target:
                lo = mid + 1
            else:
                hi = mid - 1
        return -1

    sorted_arr = [1, 3, 5, 7, 9, 11, 13]
    print(f"binary_search({sorted_arr}, 7):  index={binary_search(sorted_arr, 7)}")
    print(f"binary_search({sorted_arr}, 4):  index={binary_search(sorted_arr, 4)}")

    # --- Merge two sorted lists ---
    def merge_sorted(a: List[int], b: List[int]) -> List[int]:
        result: List[int] = []
        i = j = 0
        while i < len(a) and j < len(b):
            if a[i] < b[j]:
                result.append(a[i])
                i += 1
            else:
                result.append(b[j])
                j += 1
        result.extend(a[i:])
        result.extend(b[j:])
        return result

    print(f"merge [1,3,5] + [2,4,6]: {merge_sorted([1, 3, 5], [2, 4, 6])}")


# ═══════════════════════════════════════════════════════════════════════════════
# 14. DECORATORS
# ═══════════════════════════════════════════════════════════════════════════════

def demo_decorators() -> None:
    print("\n" + "=" * 60)
    print("14. DECORATORS")
    print("=" * 60)

    # Simple decorator
    def timer(func):
        import time
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            elapsed = time.perf_counter() - start
            print(f"  {func.__name__} took {elapsed:.6f}s")
            return result
        return wrapper

    @timer
    def slow_add(a: int, b: int) -> int:
        import time
        time.sleep(0.001)
        return a + b

    result = slow_add(3, 4)
    print(f"  slow_add(3,4) = {result}")

    # Decorator with arguments
    def retry(max_attempts: int):
        def decorator(func):
            def wrapper(*args, **kwargs):
                for attempt in range(1, max_attempts + 1):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        if attempt == max_attempts:
                            raise
                        print(f"    retry {attempt}/{max_attempts} after: {e}")
            return wrapper
        return decorator

    @retry(max_attempts=3)
    def flaky_func() -> str:
        import random
        if random.random() < 0.7:
            raise RuntimeError("transient error")
        return "success"

    try:
        print(f"  flaky_func: {flaky_func()}")
    except RuntimeError:
        print("  flaky_func: failed after 3 retries")


# ═══════════════════════════════════════════════════════════════════════════════
# 15. CLASSES — __init__, __str__, __repr__, inheritance, @property
# ═══════════════════════════════════════════════════════════════════════════════

def demo_classes() -> None:
    print("\n" + "=" * 60)
    print("15. CLASSES")
    print("=" * 60)

    class Employee:
        """Represents an employee with salary management."""

        company = "Acme Corp"  # class variable

        def __init__(self, name: str, salary: float) -> None:
            self.name = name
            self._salary = salary  # "protected" by convention

        def __str__(self) -> str:
            return f"{self.name} (${self._salary:,.2f})"

        def __repr__(self) -> str:
            return f"Employee(name={self.name!r}, salary={self._salary})"

        @property
        def salary(self) -> float:
            """Getter — access like an attribute."""
            return self._salary

        @salary.setter
        def salary(self, value: float) -> None:
            """Setter — validate on assignment."""
            if value < 0:
                raise ValueError("Salary cannot be negative")
            self._salary = value

        def give_raise(self, pct: float) -> None:
            self._salary *= (1 + pct / 100)

    # Inheritance
    class Manager(Employee):
        def __init__(self, name: str, salary: float, team: List[str]) -> None:
            super().__init__(name, salary)
            self.team = team

        def __str__(self) -> str:
            return f"{self.name} manages {self.team}"

    alice = Employee("Alice", 120000)
    print(f"  str:  {alice}")
    print(f"  repr: {repr(alice)}")
    print(f"  salary property: {alice.salary:,.0f}")

    alice.give_raise(10)
    print(f"  after 10% raise: {alice.salary:,.0f}")

    bob = Manager("Bob", 150000, ["Charlie", "Diana"])
    print(f"  manager: {bob}")
    print(f"  isinstance(bob, Employee): {isinstance(bob, Employee)}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    """Run all demos."""
    demos = [
        demo_lists,
        demo_tuples,
        demo_sets,
        demo_dicts,
        demo_loops,
        demo_functions,
        demo_lambda_map_filter_reduce,
        demo_generators,
        demo_error_handling,
        demo_file_io,
        demo_collections,
        demo_itertools,
        demo_interview_patterns,
        demo_decorators,
        demo_classes,
    ]

    for demo in demos:
        try:
            demo()
        except Exception as e:
            print(f"  ERROR in {demo.__name__}: {e}")

    print("\n" + "=" * 60)
    print("All demos complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()
