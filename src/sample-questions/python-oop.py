"""
============================================================================
Data Engineer / Senior Python Developer Interview — OOP & Typing Deep Dive
============================================================================
30 most-asked OOP and type-system questions, each shown as working code.

Topics covered:
  Q01  Class basics — __init__, instance vs class variables
  Q02  __str__ vs __repr__
  Q03  @property — getter / setter / deleter
  Q04  @classmethod vs @staticmethod
  Q05  Inheritance and super()
  Q06  Multiple inheritance and MRO (C3 linearisation)
  Q07  isinstance() vs issubclass()
  Q08  Operator overloading (__eq__, __lt__, __add__, __hash__)
  Q09  __slots__ — memory and attribute control
  Q10  __new__ vs __init__ — construction vs initialisation
  Q11  Abstract Base Classes (ABC)
  Q12  Protocols (structural subtyping / duck typing)
  Q13  Dataclasses — @dataclass, field(), frozen, ordering
  Q14  typing.NamedTuple
  Q15  Generics — TypeVar, Generic[T]
  Q16  Type aliases and Union / Optional / Literal
  Q17  Callable, overload, TYPE_CHECKING
  Q18  Descriptors — __get__, __set__, __delete__
  Q19  Context manager — __enter__ / __exit__ and contextlib
  Q20  Iterator protocol — __iter__ / __next__
  Q21  __call__ — making instances callable
  Q22  Metaclasses — type as metaclass, custom metaclass
  Q23  Mixin pattern
  Q24  Composition over inheritance
  Q25  Singleton pattern (thread-safe)
  Q26  Factory / Class-method factory pattern
  Q27  Encapsulation — public / _protected / __private (name mangling)
  Q28  Polymorphism — duck typing + runtime dispatch
  Q29  Class decorators
  Q30  Putting it all together — production-style typed pipeline class

Run: python python-oop.py
============================================================================
"""

from __future__ import annotations

import abc
import contextlib
import threading
from collections.abc import Iterator
from dataclasses import dataclass, field
from functools import total_ordering
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    Dict,
    Generic,
    List,
    Literal,
    Optional,
    Protocol,
    TypeVar,
    Union,
    overload,
    runtime_checkable,
)

if TYPE_CHECKING:
    pass  # safe imports only used by type checkers


# ═══════════════════════════════════════════════════════════════════════════════
# Q01  Class basics — __init__, instance variables vs class variables
# ═══════════════════════════════════════════════════════════════════════════════

def q01_class_basics() -> None:
    print("=" * 60)
    print("Q01  Class basics — instance vs class variables")
    print("=" * 60)

    class BankAccount:
        bank_name: ClassVar[str] = "RBC"   # shared across ALL instances
        _count: ClassVar[int] = 0

        def __init__(self, owner: str, balance: float = 0.0) -> None:
            self.owner = owner              # instance variable — unique per object
            self.balance = balance
            BankAccount._count += 1

        def deposit(self, amount: float) -> None:
            self.balance += amount

        def withdraw(self, amount: float) -> None:
            if amount > self.balance:
                raise ValueError("Insufficient funds")
            self.balance -= amount

        @classmethod
        def total_accounts(cls) -> int:
            return cls._count

    a1 = BankAccount("Alice", 1000)
    a2 = BankAccount("Bob", 500)
    a1.deposit(200)
    a2.withdraw(100)

    print(f"  a1.balance:           {a1.balance}")
    print(f"  a2.balance:           {a2.balance}")
    print(f"  class var bank_name:  {BankAccount.bank_name}")
    print(f"  total accounts:       {BankAccount.total_accounts()}")
    # KEY: changing class var via instance creates a shadow instance var
    a1.bank_name = "TD"
    print(f"  a1.bank_name (shadow): {a1.bank_name}")
    print(f"  BankAccount.bank_name: {BankAccount.bank_name}  ← unchanged")


# ═══════════════════════════════════════════════════════════════════════════════
# Q02  __str__ vs __repr__
# ═══════════════════════════════════════════════════════════════════════════════

def q02_str_vs_repr() -> None:
    print("\n" + "=" * 60)
    print("Q02  __str__ vs __repr__")
    print("=" * 60)

    class Trade:
        def __init__(self, symbol: str, qty: int, price: float) -> None:
            self.symbol = symbol
            self.qty = qty
            self.price = price

        def __repr__(self) -> str:
            # Machine-readable: goal is eval(repr(obj)) == obj
            return f"Trade(symbol={self.symbol!r}, qty={self.qty}, price={self.price})"

        def __str__(self) -> str:
            # Human-readable: shown by print() and str()
            return f"[Trade] {self.symbol} x{self.qty} @ ${self.price:.2f}"

    t = Trade("AAPL", 100, 182.50)
    print(f"  str(t):   {str(t)}")
    print(f"  repr(t):  {repr(t)}")
    print(f"  in list:  {[t]}")  # list uses repr


# ═══════════════════════════════════════════════════════════════════════════════
# Q03  @property — getter / setter / deleter
# ═══════════════════════════════════════════════════════════════════════════════

def q03_property() -> None:
    print("\n" + "=" * 60)
    print("Q03  @property — getter / setter / deleter")
    print("=" * 60)

    class Temperature:
        def __init__(self, celsius: float) -> None:
            self._celsius = celsius   # underscore = "internal" by convention

        @property
        def celsius(self) -> float:
            """Read celsius."""
            return self._celsius

        @celsius.setter
        def celsius(self, value: float) -> None:
            """Validate on assignment."""
            if value < -273.15:
                raise ValueError(f"Temperature below absolute zero: {value}")
            self._celsius = value

        @celsius.deleter
        def celsius(self) -> None:
            print("  deleter called — resetting to 0")
            self._celsius = 0.0

        @property
        def fahrenheit(self) -> float:
            """Derived, read-only property."""
            return self._celsius * 9 / 5 + 32

    t = Temperature(100)
    print(f"  celsius:    {t.celsius}")
    print(f"  fahrenheit: {t.fahrenheit}")
    t.celsius = 0
    print(f"  set to 0°C -> {t.fahrenheit}°F")
    del t.celsius
    print(f"  after delete: {t.celsius}°C")
    try:
        t.celsius = -300
    except ValueError as e:
        print(f"  caught: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# Q04  @classmethod vs @staticmethod
# ═══════════════════════════════════════════════════════════════════════════════

def q04_classmethod_staticmethod() -> None:
    print("\n" + "=" * 60)
    print("Q04  @classmethod vs @staticmethod")
    print("=" * 60)

    class FundReport:
        _registry: ClassVar[List[FundReport]] = []

        def __init__(self, fund_id: str, report_date: str) -> None:
            self.fund_id = fund_id
            self.report_date = report_date
            FundReport._registry.append(self)

        @classmethod
        def from_dict(cls, data: Dict[str, str]) -> "FundReport":
            """Alternative constructor — classmethod receives cls, not self."""
            return cls(data["fund_id"], data["report_date"])

        @classmethod
        def all_reports(cls) -> List["FundReport"]:
            return cls._registry

        @staticmethod
        def is_valid_date(date_str: str) -> bool:
            """Utility — no access to class or instance needed."""
            parts = date_str.split("-")
            return len(parts) == 3 and all(p.isdigit() for p in parts)

        def __repr__(self) -> str:
            return f"FundReport({self.fund_id}, {self.report_date})"

    r1 = FundReport("FUND-001", "2026-07-01")
    r2 = FundReport.from_dict({"fund_id": "FUND-002", "report_date": "2026-07-02"})
    print(f"  r1:               {r1}")
    print(f"  r2 (from_dict):   {r2}")
    print(f"  all_reports:      {FundReport.all_reports()}")
    print(f"  valid date:       {FundReport.is_valid_date('2026-07-01')}")
    print(f"  invalid date:     {FundReport.is_valid_date('not-a-date')}")
    # staticmethod can also be called on instance
    print(f"  via instance:     {r1.is_valid_date('2026-07-01')}")


# ═══════════════════════════════════════════════════════════════════════════════
# Q05  Inheritance and super()
# ═══════════════════════════════════════════════════════════════════════════════

def q05_inheritance_super() -> None:
    print("\n" + "=" * 60)
    print("Q05  Inheritance and super()")
    print("=" * 60)

    class Asset:
        def __init__(self, asset_id: str, value: float) -> None:
            self.asset_id = asset_id
            self.value = value

        def describe(self) -> str:
            return f"Asset {self.asset_id}: ${self.value:,.0f}"

        def risk_score(self) -> float:
            return 0.0   # base default

    class EquityAsset(Asset):
        def __init__(self, asset_id: str, value: float, ticker: str) -> None:
            super().__init__(asset_id, value)  # ALWAYS call super().__init__
            self.ticker = ticker

        def describe(self) -> str:
            base = super().describe()          # extend parent behaviour
            return f"{base} [{self.ticker}]"

        def risk_score(self) -> float:
            return 0.75

    class BondAsset(Asset):
        def __init__(self, asset_id: str, value: float, rating: str) -> None:
            super().__init__(asset_id, value)
            self.rating = rating

        def risk_score(self) -> float:
            return 0.25 if self.rating in ("AAA", "AA") else 0.50

    eq = EquityAsset("A001", 500_000, "AAPL")
    bond = BondAsset("B001", 1_000_000, "AA")

    print(f"  {eq.describe()}")
    print(f"  equity risk: {eq.risk_score()}")
    print(f"  {bond.describe()}")
    print(f"  bond risk:   {bond.risk_score()}")
    print(f"  isinstance(eq, Asset):   {isinstance(eq, Asset)}")
    print(f"  issubclass(EquityAsset, Asset): {issubclass(EquityAsset, Asset)}")


# ═══════════════════════════════════════════════════════════════════════════════
# Q06  Multiple inheritance and MRO (C3 linearisation)
# ═══════════════════════════════════════════════════════════════════════════════

def q06_mro() -> None:
    print("\n" + "=" * 60)
    print("Q06  Multiple inheritance and MRO")
    print("=" * 60)

    class Loggable:
        def log(self) -> str:
            return "[Loggable]"

    class Auditable:
        def log(self) -> str:
            return "[Auditable]"

    class RiskItem(Loggable, Auditable):
        """MRO: RiskItem -> Loggable -> Auditable -> object"""
        pass

    r = RiskItem()
    print(f"  r.log():       {r.log()}")           # Loggable wins (left-to-right)
    print(f"  MRO:           {[c.__name__ for c in RiskItem.__mro__]}")

    # Diamond problem — super() resolves correctly via MRO
    class A:
        def greet(self) -> str:
            return "A"

    class B(A):
        def greet(self) -> str:
            return "B->" + super().greet()

    class C(A):
        def greet(self) -> str:
            return "C->" + super().greet()

    class D(B, C):
        def greet(self) -> str:
            return "D->" + super().greet()

    d = D()
    print(f"  diamond D.greet(): {d.greet()}")   # D->B->C->A
    print(f"  D MRO: {[c.__name__ for c in D.__mro__]}")


# ═══════════════════════════════════════════════════════════════════════════════
# Q07  isinstance() vs issubclass() — with ABC registration
# ═══════════════════════════════════════════════════════════════════════════════

def q07_isinstance_issubclass() -> None:
    print("\n" + "=" * 60)
    print("Q07  isinstance() vs issubclass()")
    print("=" * 60)

    class Animal:
        pass

    class Dog(Animal):
        pass

    class Cat(Animal):
        pass

    dog = Dog()
    print(f"  isinstance(dog, Dog):    {isinstance(dog, Dog)}")
    print(f"  isinstance(dog, Animal): {isinstance(dog, Animal)}")   # True — checks hierarchy
    print(f"  isinstance(dog, Cat):    {isinstance(dog, Cat)}")
    print(f"  issubclass(Dog, Animal): {issubclass(Dog, Animal)}")
    print(f"  issubclass(Dog, Cat):    {issubclass(Dog, Cat)}")

    # isinstance with tuple of types
    print(f"  isinstance(dog,(Cat,Dog)): {isinstance(dog, (Cat, Dog))}")

    # virtual subclass via ABC
    class Readable(abc.ABC):
        pass

    @Readable.register
    class CSVFile:
        pass  # does NOT inherit from Readable but is "registered"

    csv = CSVFile()
    print(f"  CSVFile registered as Readable: {isinstance(csv, Readable)}")


# ═══════════════════════════════════════════════════════════════════════════════
# Q08  Operator overloading — __eq__, __lt__, __add__, __hash__
# ═══════════════════════════════════════════════════════════════════════════════

def q08_operator_overloading() -> None:
    print("\n" + "=" * 60)
    print("Q08  Operator overloading")
    print("=" * 60)

    @total_ordering   # only need __eq__ + one comparison; rest auto-generated
    class Money:
        def __init__(self, amount: float, currency: str = "USD") -> None:
            self.amount = amount
            self.currency = currency

        def __eq__(self, other: object) -> bool:
            if not isinstance(other, Money):
                return NotImplemented
            return self.amount == other.amount and self.currency == other.currency

        def __lt__(self, other: "Money") -> bool:
            if self.currency != other.currency:
                raise ValueError("Cannot compare different currencies")
            return self.amount < other.amount

        def __add__(self, other: "Money") -> "Money":
            if self.currency != other.currency:
                raise ValueError("Cannot add different currencies")
            return Money(self.amount + other.amount, self.currency)

        def __hash__(self) -> int:
            # Must define when __eq__ is defined (otherwise unhashable)
            return hash((self.amount, self.currency))

        def __repr__(self) -> str:
            return f"Money({self.amount}, {self.currency!r})"

    a = Money(100, "USD")
    b = Money(200, "USD")
    c = Money(100, "USD")

    print(f"  a == c:   {a == c}")       # True
    print(f"  a == b:   {a == b}")       # False
    print(f"  a < b:    {a < b}")        # True
    print(f"  a > b:    {a > b}")        # False (from @total_ordering)
    print(f"  a + b:    {a + b}")
    print(f"  set:      {{{a}, {b}, {c}}}")   # hash deduplicates a and c


# ═══════════════════════════════════════════════════════════════════════════════
# Q09  __slots__ — memory optimisation and attribute restriction
# ═══════════════════════════════════════════════════════════════════════════════

def q09_slots() -> None:
    print("\n" + "=" * 60)
    print("Q09  __slots__")
    print("=" * 60)

    import sys

    class ChunkNoSlots:
        def __init__(self, text: str, token_count: int) -> None:
            self.text = text
            self.token_count = token_count

    class ChunkWithSlots:
        __slots__ = ("text", "token_count")

        def __init__(self, text: str, token_count: int) -> None:
            self.text = text
            self.token_count = token_count

    c1 = ChunkNoSlots("hello world", 2)
    c2 = ChunkWithSlots("hello world", 2)

    print(f"  no-slots  size: {sys.getsizeof(c1)} bytes")
    print(f"  with-slots size: {sys.getsizeof(c2)} bytes")
    print(f"  no-slots has __dict__:  {hasattr(c1, '__dict__')}")
    print(f"  slots has __dict__:     {hasattr(c2, '__dict__')}")

    # __slots__ prevents adding arbitrary attributes
    c1.extra = "allowed"
    try:
        c2.extra = "not allowed"
    except AttributeError as e:
        print(f"  slots blocks new attr:  {e}")

    # Useful for millions of lightweight objects (e.g. embedding chunks in ETL)
    N = 100_000
    chunks_plain = [ChunkNoSlots("x", i) for i in range(N)]
    chunks_slots = [ChunkWithSlots("x", i) for i in range(N)]
    size_plain = sum(sys.getsizeof(c) for c in chunks_plain)
    size_slots = sum(sys.getsizeof(c) for c in chunks_slots)
    print(f"  {N:,} plain objects: {size_plain:,} bytes")
    print(f"  {N:,} slots objects: {size_slots:,} bytes  ← savings: {size_plain - size_slots:,}")


# ═══════════════════════════════════════════════════════════════════════════════
# Q10  __new__ vs __init__
# ═══════════════════════════════════════════════════════════════════════════════

def q10_new_vs_init() -> None:
    print("\n" + "=" * 60)
    print("Q10  __new__ vs __init__")
    print("=" * 60)

    # __new__ creates the instance (before __init__ receives it)
    # __init__ initialises the already-created instance

    class ImmutablePoint:
        """Demonstrates __new__ for immutable-style construction."""
        __slots__ = ("x", "y")

        def __new__(cls, x: float, y: float) -> "ImmutablePoint":
            print(f"  __new__ called (cls={cls.__name__})")
            instance = super().__new__(cls)
            return instance

        def __init__(self, x: float, y: float) -> None:
            print(f"  __init__ called")
            object.__setattr__(self, "x", x)
            object.__setattr__(self, "y", y)

        def __setattr__(self, name: str, value: Any) -> None:
            raise AttributeError("ImmutablePoint is immutable")

        def __repr__(self) -> str:
            return f"ImmutablePoint({self.x}, {self.y})"

    p = ImmutablePoint(3.0, 4.0)
    print(f"  p = {p}")
    try:
        p.x = 10  # type: ignore
    except AttributeError as e:
        print(f"  immutable blocked: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# Q11  Abstract Base Classes (ABC)
# ═══════════════════════════════════════════════════════════════════════════════

def q11_abc() -> None:
    print("\n" + "=" * 60)
    print("Q11  Abstract Base Classes (ABC)")
    print("=" * 60)

    class VectorStore(abc.ABC):
        """Contract every vector backend must fulfil."""

        @abc.abstractmethod
        def upsert(self, fund_id: str, chunks: List[str]) -> int:
            """Return number of chunks written."""
            ...

        @abc.abstractmethod
        def search(self, fund_id: str, query: str, k: int = 5) -> List[str]:
            """Return top-k matching chunks."""
            ...

        def health_check(self) -> bool:
            """Concrete method — shared default behaviour."""
            return True

    # Cannot instantiate ABC directly
    try:
        VectorStore()  # type: ignore
    except TypeError as e:
        print(f"  cannot instantiate ABC: {e}")

    class InMemoryVectorStore(VectorStore):
        def __init__(self) -> None:
            self._store: Dict[str, List[str]] = {}

        def upsert(self, fund_id: str, chunks: List[str]) -> int:
            self._store[fund_id] = chunks
            return len(chunks)

        def search(self, fund_id: str, query: str, k: int = 5) -> List[str]:
            return (self._store.get(fund_id) or [])[:k]

    store = InMemoryVectorStore()
    written = store.upsert("FUND-001", ["VaR exceeded", "CVA spike", "RWA delta"])
    results = store.search("FUND-001", "VaR", k=2)
    print(f"  upserted:   {written} chunks")
    print(f"  search top2: {results}")
    print(f"  health:      {store.health_check()}")


# ═══════════════════════════════════════════════════════════════════════════════
# Q12  Protocol — structural subtyping (duck typing with types)
# ═══════════════════════════════════════════════════════════════════════════════

def q12_protocol() -> None:
    print("\n" + "=" * 60)
    print("Q12  Protocol (structural subtyping)")
    print("=" * 60)

    @runtime_checkable
    class Serialisable(Protocol):
        """Any class with to_dict() satisfies this Protocol — no inheritance needed."""

        def to_dict(self) -> Dict[str, Any]:
            ...

    class Finding:
        def __init__(self, severity: str, description: str) -> None:
            self.severity = severity
            self.description = description

        def to_dict(self) -> Dict[str, Any]:
            return {"severity": self.severity, "description": self.description}

    class RawRecord:
        def __init__(self, data: str) -> None:
            self.data = data

        def to_dict(self) -> Dict[str, Any]:
            return {"raw": self.data}

    def persist(obj: Serialisable) -> str:
        import json
        return json.dumps(obj.to_dict())

    f = Finding("HIGH", "VaR threshold exceeded")
    r = RawRecord("raw-payload")

    print(f"  Finding serialised:    {persist(f)}")
    print(f"  RawRecord serialised:  {persist(r)}")
    # Runtime check (needs @runtime_checkable)
    print(f"  isinstance(f, Serialisable): {isinstance(f, Serialisable)}")
    print(f"  isinstance(42, Serialisable): {isinstance(42, Serialisable)}")


# ═══════════════════════════════════════════════════════════════════════════════
# Q13  @dataclass — field(), frozen, ordering, post_init
# ═══════════════════════════════════════════════════════════════════════════════

def q13_dataclass() -> None:
    print("\n" + "=" * 60)
    print("Q13  @dataclass")
    print("=" * 60)

    @dataclass(order=True, frozen=False)
    class RiskFinding:
        # sort_index is a hidden ordering field (excluded from repr/init)
        sort_index: float = field(init=False, repr=False)
        severity: str                             # "HIGH" / "MEDIUM" / "LOW"
        description: str
        var_delta: float = 0.0
        tags: List[str] = field(default_factory=list)

        _SEVERITY_RANK: ClassVar[Dict[str, int]] = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}

        def __post_init__(self) -> None:
            # computed after __init__
            self.sort_index = self._SEVERITY_RANK.get(self.severity, 0)

    @dataclass(frozen=True)   # frozen=True -> immutable -> hashable
    class FundKey:
        fund_id: str
        report_date: str

    f1 = RiskFinding("HIGH", "VaR breach", var_delta=0.15, tags=["market"])
    f2 = RiskFinding("LOW", "Minor drift", var_delta=0.02)
    f3 = RiskFinding("MEDIUM", "CVA spike", var_delta=0.08)

    findings = sorted([f1, f2, f3], reverse=True)  # sorts by sort_index
    for f in findings:
        print(f"  {f.severity}: {f.description} (VaR Δ {f.var_delta})")

    key = FundKey("FUND-001", "2026-07-01")
    cache: Dict[FundKey, str] = {key: "cached-report"}
    print(f"  frozen FundKey in dict: {cache[key][:6]}...")

    # asdict
    from dataclasses import asdict
    print(f"  asdict(f1): {asdict(f1)}")


# ═══════════════════════════════════════════════════════════════════════════════
# Q14  typing.NamedTuple
# ═══════════════════════════════════════════════════════════════════════════════

def q14_named_tuple() -> None:
    print("\n" + "=" * 60)
    print("Q14  typing.NamedTuple")
    print("=" * 60)

    from typing import NamedTuple

    class ChunkRecord(NamedTuple):
        fund_id: str
        chunk_index: int
        text: str
        token_count: int
        section_title: str = "unknown"

    c = ChunkRecord("FUND-001", 0, "VaR exceeded threshold", 4)
    print(f"  ChunkRecord:      {c}")
    print(f"  fund_id:          {c.fund_id}")
    print(f"  as dict:          {c._asdict()}")
    print(f"  tuple unpacking:  {c[0]}, {c[1]}, {c[2][:10]}...")
    print(f"  default title:    {c.section_title}")

    # NamedTuple vs dataclass: NamedTuple is immutable, tuple-compatible
    try:
        c.fund_id = "FUND-999"  # type: ignore
    except AttributeError as e:
        print(f"  immutable: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# Q15  Generics — TypeVar and Generic[T]
# ═══════════════════════════════════════════════════════════════════════════════

def q15_generics() -> None:
    print("\n" + "=" * 60)
    print("Q15  Generics — TypeVar and Generic[T]")
    print("=" * 60)

    T = TypeVar("T")
    KT = TypeVar("KT")
    VT = TypeVar("VT")

    class Stack(Generic[T]):
        """Type-safe stack container."""

        def __init__(self) -> None:
            self._items: List[T] = []

        def push(self, item: T) -> None:
            self._items.append(item)

        def pop(self) -> T:
            if not self._items:
                raise IndexError("Stack is empty")
            return self._items.pop()

        def peek(self) -> T:
            return self._items[-1]

        def __len__(self) -> int:
            return len(self._items)

        def __repr__(self) -> str:
            return f"Stack({self._items})"

    # Typed as Stack[str]
    s: Stack[str] = Stack()
    s.push("ingest")
    s.push("retrieve")
    s.push("analyze")
    print(f"  Stack[str]:  {s}")
    print(f"  peek:        {s.peek()}")
    print(f"  pop:         {s.pop()}")
    print(f"  remaining:   {s}")

    # Generic function
    def first_or_default(items: List[T], default: T) -> T:
        return items[0] if items else default

    print(f"  first_or_default([1,2], 0): {first_or_default([1, 2], 0)}")
    print(f"  first_or_default([], 'N/A'): {first_or_default([], 'N/A')}")


# ═══════════════════════════════════════════════════════════════════════════════
# Q16  Type aliases, Union, Optional, Literal
# ═══════════════════════════════════════════════════════════════════════════════

def q16_type_aliases() -> None:
    print("\n" + "=" * 60)
    print("Q16  Type aliases / Union / Optional / Literal")
    print("=" * 60)

    # Type alias
    FundID = str
    Score = float
    RiskMap = Dict[FundID, Score]

    # Union — accepts int OR float OR str
    def format_value(v: Union[int, float, str]) -> str:
        return f"{v:.2f}" if isinstance(v, float) else str(v)

    # Optional[X] is shorthand for Union[X, None]
    def find_fund(fund_id: str, registry: Dict[str, str]) -> Optional[str]:
        return registry.get(fund_id)

    # Literal — restrict to specific values
    Severity = Literal["HIGH", "MEDIUM", "LOW"]

    def classify(score: float) -> Severity:
        if score > 0.8:
            return "HIGH"
        elif score > 0.4:
            return "MEDIUM"
        return "LOW"

    reg = {"FUND-001": "Global Equity Fund"}
    print(f"  find FUND-001:      {find_fund('FUND-001', reg)}")
    print(f"  find FUND-999:      {find_fund('FUND-999', reg)}")
    print(f"  format_value(3.14): {format_value(3.14)}")
    print(f"  format_value(42):   {format_value(42)}")
    print(f"  classify(0.9):      {classify(0.9)}")
    print(f"  classify(0.5):      {classify(0.5)}")
    print(f"  classify(0.1):      {classify(0.1)}")


# ═══════════════════════════════════════════════════════════════════════════════
# Q17  Callable, @overload, TYPE_CHECKING
# ═══════════════════════════════════════════════════════════════════════════════

def q17_callable_overload() -> None:
    print("\n" + "=" * 60)
    print("Q17  Callable / @overload / TYPE_CHECKING")
    print("=" * 60)

    # Callable[[ArgTypes...], ReturnType]
    Transform = Callable[[str], str]

    def apply_transforms(text: str, transforms: List[Transform]) -> str:
        for fn in transforms:
            text = fn(text)
        return text

    result = apply_transforms(
        "  Hello World  ",
        [str.strip, str.lower, lambda s: s.replace(" ", "_")],
    )
    print(f"  apply_transforms: {result!r}")

    # @overload — separate type signatures for same function
    @overload
    def load_data(source: str) -> List[str]: ...
    @overload
    def load_data(source: List[str]) -> List[str]: ...

    def load_data(source: Union[str, List[str]]) -> List[str]:  # type: ignore[misc]
        if isinstance(source, str):
            return [f"loaded from file: {source}"]
        return source

    print(f"  load_data(str):  {load_data('data.json')}")
    print(f"  load_data(list): {load_data(['a', 'b'])}")


# ═══════════════════════════════════════════════════════════════════════════════
# Q18  Descriptors — __get__, __set__, __delete__
# ═══════════════════════════════════════════════════════════════════════════════

def q18_descriptors() -> None:
    print("\n" + "=" * 60)
    print("Q18  Descriptors")
    print("=" * 60)

    class PositiveFloat:
        """A descriptor that enforces positive float values."""

        def __set_name__(self, owner: type, name: str) -> None:
            self._name = f"_{name}"   # store in mangled private attr

        def __get__(self, obj: Any, objtype: Any = None) -> float:
            if obj is None:
                return self  # type: ignore  # class-level access
            return getattr(obj, self._name, 0.0)

        def __set__(self, obj: Any, value: float) -> None:
            if not isinstance(value, (int, float)) or value <= 0:
                raise ValueError(f"{self._name} must be a positive number, got {value}")
            setattr(obj, self._name, float(value))

    class Position:
        notional = PositiveFloat()
        price    = PositiveFloat()

        def __init__(self, notional: float, price: float) -> None:
            self.notional = notional
            self.price = price

        def market_value(self) -> float:
            return self.notional * self.price

    p = Position(1_000_000, 182.5)
    print(f"  market_value: {p.market_value():,.2f}")

    try:
        p.notional = -500
    except ValueError as e:
        print(f"  blocked: {e}")

    try:
        p.price = 0
    except ValueError as e:
        print(f"  blocked: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# Q19  Context manager — __enter__ / __exit__ and @contextmanager
# ═══════════════════════════════════════════════════════════════════════════════

def q19_context_manager() -> None:
    print("\n" + "=" * 60)
    print("Q19  Context manager — __enter__ / __exit__ / @contextmanager")
    print("=" * 60)

    # Class-based context manager
    class DBConnection:
        def __init__(self, db_url: str) -> None:
            self.db_url = db_url
            self.conn: Optional[str] = None

        def __enter__(self) -> "DBConnection":
            self.conn = f"conn://{self.db_url}"
            print(f"  [open]  {self.conn}")
            return self

        def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
            print(f"  [close] {self.conn}")
            self.conn = None
            if exc_type is ValueError:
                print(f"  [suppress] ValueError: {exc_val}")
                return True   # suppress this exception
            return False       # re-raise all others

        def query(self, sql: str) -> List[str]:
            return [f"row from {self.conn}: {sql}"]

    with DBConnection("pgvector:5432") as db:
        rows = db.query("SELECT * FROM chunks LIMIT 2")
        print(f"  rows: {rows}")

    # __exit__ suppresses ValueError
    with DBConnection("pgvector:5432") as db:
        raise ValueError("test suppression")

    # Generator-based context manager via @contextmanager
    @contextlib.contextmanager
    def timed_block(label: str) -> Iterator[None]:
        import time
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed = time.perf_counter() - start
            print(f"  [{label}] elapsed: {elapsed:.4f}s")

    with timed_block("embedding ETL"):
        _ = sum(range(1_000_000))


# ═══════════════════════════════════════════════════════════════════════════════
# Q20  Iterator protocol — __iter__ / __next__
# ═══════════════════════════════════════════════════════════════════════════════

def q20_iterator_protocol() -> None:
    print("\n" + "=" * 60)
    print("Q20  Iterator protocol — __iter__ / __next__")
    print("=" * 60)

    class ChunkBatchIterator:
        """Iterates over chunks in configurable batch sizes (like a Spark partition)."""

        def __init__(self, chunks: List[str], batch_size: int = 3) -> None:
            self._chunks = chunks
            self._batch_size = batch_size
            self._index = 0

        def __iter__(self) -> "ChunkBatchIterator":
            return self        # the iterator IS the iterable here

        def __next__(self) -> List[str]:
            if self._index >= len(self._chunks):
                raise StopIteration
            batch = self._chunks[self._index: self._index + self._batch_size]
            self._index += self._batch_size
            return batch

    chunks = [f"chunk_{i}" for i in range(10)]
    batches = ChunkBatchIterator(chunks, batch_size=3)

    for i, batch in enumerate(batches):
        print(f"  batch {i}: {batch}")

    # Iterable (has __iter__ returning an iterator) vs Iterator (__next__)
    class NumberRange:
        def __init__(self, stop: int) -> None:
            self.stop = stop

        def __iter__(self) -> Iterator[int]:  # returns a generator = iterator
            for i in range(self.stop):
                yield i * i

    print(f"  squares:   {list(NumberRange(5))}")


# ═══════════════════════════════════════════════════════════════════════════════
# Q21  __call__ — making instances callable
# ═══════════════════════════════════════════════════════════════════════════════

def q21_callable_objects() -> None:
    print("\n" + "=" * 60)
    print("Q21  __call__")
    print("=" * 60)

    class ThresholdClassifier:
        """Callable object — stateful function."""

        def __init__(self, threshold: float) -> None:
            self.threshold = threshold
            self.call_count = 0

        def __call__(self, score: float) -> str:
            self.call_count += 1
            return "BREACH" if score > self.threshold else "OK"

        def __repr__(self) -> str:
            return f"ThresholdClassifier(threshold={self.threshold})"

    classify = ThresholdClassifier(threshold=0.75)
    scores = [0.5, 0.8, 0.3, 0.9, 0.7]
    results = [classify(s) for s in scores]
    print(f"  classifier: {classify}")
    print(f"  results:    {results}")
    print(f"  calls made: {classify.call_count}")
    print(f"  callable(): {callable(classify)}")


# ═══════════════════════════════════════════════════════════════════════════════
# Q22  Metaclasses — type() and custom metaclass
# ═══════════════════════════════════════════════════════════════════════════════

def q22_metaclasses() -> None:
    print("\n" + "=" * 60)
    print("Q22  Metaclasses")
    print("=" * 60)

    # type() is the default metaclass
    print(f"  type(int):    {type(int)}")
    print(f"  type(str):    {type(str)}")

    # Create a class dynamically with type()
    DynamicClass = type(
        "DynamicClass",              # name
        (object,),                   # bases
        {"greet": lambda self: "hi", "x": 42},  # namespace
    )
    d = DynamicClass()
    print(f"  dynamic class: {d.greet()}, x={d.x}")

    # Custom metaclass — enforce all method names are lowercase
    class LowercaseMethodsMeta(type):
        def __new__(mcs, name: str, bases: tuple, namespace: dict) -> type:
            for key in namespace:
                if not key.startswith("_") and not key.islower():
                    raise TypeError(f"Method names must be lowercase, got: {key!r}")
            return super().__new__(mcs, name, bases, namespace)

    class GoodClass(metaclass=LowercaseMethodsMeta):
        def compute(self) -> int:
            return 42

    g = GoodClass()
    print(f"  GoodClass.compute(): {g.compute()}")

    try:
        class BadClass(metaclass=LowercaseMethodsMeta):
            def ComputeRisk(self) -> int:   # uppercase -> rejected
                return 0
    except TypeError as e:
        print(f"  metaclass blocked:   {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# Q23  Mixin pattern
# ═══════════════════════════════════════════════════════════════════════════════

def q23_mixin() -> None:
    print("\n" + "=" * 60)
    print("Q23  Mixin pattern")
    print("=" * 60)

    class JSONMixin:
        """Add to_json() to any class that has to_dict()."""
        def to_json(self) -> str:
            import json
            return json.dumps(self.to_dict(), indent=2)  # type: ignore[attr-defined]

    class LogMixin:
        """Add audit_log() to any class."""
        def audit_log(self) -> str:
            return f"[AUDIT] {self.__class__.__name__} accessed"

    class RiskReport:
        def __init__(self, fund_id: str, status: str) -> None:
            self.fund_id = fund_id
            self.status = status

        def to_dict(self) -> Dict[str, str]:
            return {"fund_id": self.fund_id, "status": self.status}

    class EnrichedRiskReport(JSONMixin, LogMixin, RiskReport):
        pass

    r = EnrichedRiskReport("FUND-001", "REVIEWED")
    print(f"  to_json:\n{r.to_json()}")
    print(f"  audit:  {r.audit_log()}")
    print(f"  MRO:    {[c.__name__ for c in EnrichedRiskReport.__mro__]}")


# ═══════════════════════════════════════════════════════════════════════════════
# Q24  Composition over inheritance
# ═══════════════════════════════════════════════════════════════════════════════

def q24_composition() -> None:
    print("\n" + "=" * 60)
    print("Q24  Composition over inheritance")
    print("=" * 60)

    # Prefer: "has-a" (composition) over "is-a" (deep inheritance chains)

    class Embedder:
        def embed(self, text: str) -> List[float]:
            return [float(ord(c)) for c in text[:4]]   # mock

    class Chunker:
        def chunk(self, text: str, size: int = 50) -> List[str]:
            return [text[i: i + size] for i in range(0, len(text), size)]

    class EmbeddingPipeline:
        """Composed of a Chunker and an Embedder — no inheritance needed."""

        def __init__(self, chunker: Chunker, embedder: Embedder) -> None:
            self._chunker = chunker
            self._embedder = embedder

        def run(self, text: str) -> List[List[float]]:
            chunks = self._chunker.chunk(text)
            return [self._embedder.embed(c) for c in chunks]

    pipeline = EmbeddingPipeline(Chunker(), Embedder())
    result = pipeline.run("Risk assessment report: VaR exceeded on 2026-07-01.")
    print(f"  chunks embedded: {len(result)}")
    print(f"  first vector:    {result[0][:4]}...")

    # Swap the embedder without touching the pipeline
    class FancyEmbedder(Embedder):
        def embed(self, text: str) -> List[float]:
            return [1.0, 2.0, 3.0, 4.0]   # mock fancy

    fancy_pipeline = EmbeddingPipeline(Chunker(), FancyEmbedder())
    print(f"  fancy vectors:   {fancy_pipeline.run('hello')[0]}")


# ═══════════════════════════════════════════════════════════════════════════════
# Q25  Singleton pattern (thread-safe)
# ═══════════════════════════════════════════════════════════════════════════════

def q25_singleton() -> None:
    print("\n" + "=" * 60)
    print("Q25  Singleton (thread-safe)")
    print("=" * 60)

    class VectorStoreRegistry:
        """Global registry — only one instance per process."""
        _instance: Optional["VectorStoreRegistry"] = None
        _lock: ClassVar[threading.Lock] = threading.Lock()

        def __new__(cls) -> "VectorStoreRegistry":
            if cls._instance is None:
                with cls._lock:
                    if cls._instance is None:   # double-checked locking
                        cls._instance = super().__new__(cls)
                        cls._instance._stores: Dict[str, Any] = {}
            return cls._instance

        def register(self, name: str, store: Any) -> None:
            self._stores[name] = store

        def get(self, name: str) -> Optional[Any]:
            return self._stores.get(name)

    r1 = VectorStoreRegistry()
    r2 = VectorStoreRegistry()
    r1.register("in_memory", {"chunks": []})

    print(f"  r1 is r2:          {r1 is r2}")           # True
    print(f"  r2.get('in_memory'): {r2.get('in_memory')}")   # same object
    print(f"  id(r1)==id(r2):    {id(r1) == id(r2)}")


# ═══════════════════════════════════════════════════════════════════════════════
# Q26  Factory / class-method factory pattern
# ═══════════════════════════════════════════════════════════════════════════════

def q26_factory() -> None:
    print("\n" + "=" * 60)
    print("Q26  Factory pattern")
    print("=" * 60)

    class Agent(abc.ABC):
        @abc.abstractmethod
        def run(self, context: str) -> str: ...

    class ComplianceAgent(Agent):
        def run(self, context: str) -> str:
            return f"[Compliance] checking: {context[:20]}..."

    class EscalationAgent(Agent):
        def run(self, context: str) -> str:
            return f"[Escalation] routing: {context[:20]}..."

    class MarketAgent(Agent):
        def run(self, context: str) -> str:
            return f"[Market] analysing: {context[:20]}..."

    class AgentFactory:
        _registry: ClassVar[Dict[str, type]] = {
            "compliance": ComplianceAgent,
            "escalation": EscalationAgent,
            "market":     MarketAgent,
        }

        @classmethod
        def create(cls, agent_type: str) -> Agent:
            klass = cls._registry.get(agent_type)
            if klass is None:
                raise ValueError(f"Unknown agent type: {agent_type!r}")
            return klass()

        @classmethod
        def register(cls, name: str, klass: type) -> None:
            cls._registry[name] = klass

    for agent_type in ["compliance", "market", "escalation"]:
        agent = AgentFactory.create(agent_type)
        print(f"  {agent.run('VaR threshold exceeded for FUND-001 on 2026-07-01')}")

    try:
        AgentFactory.create("unknown")
    except ValueError as e:
        print(f"  caught: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# Q27  Encapsulation — public / _protected / __private (name mangling)
# ═══════════════════════════════════════════════════════════════════════════════

def q27_encapsulation() -> None:
    print("\n" + "=" * 60)
    print("Q27  Encapsulation — name mangling")
    print("=" * 60)

    class Fund:
        def __init__(self, fund_id: str, nav: float) -> None:
            self.fund_id = fund_id          # public
            self._nav = nav                 # _protected: "please don't touch"
            self.__audit_log: List[str] = []  # __private: name-mangled

        def deposit(self, amount: float) -> None:
            self._nav += amount
            self.__audit_log.append(f"deposit {amount}")

        def get_log(self) -> List[str]:
            return list(self.__audit_log)

    f = Fund("FUND-001", 1_000_000)
    f.deposit(50_000)
    print(f"  public fund_id:     {f.fund_id}")
    print(f"  protected _nav:     {f._nav}")          # accessible but discouraged
    print(f"  audit log:          {f.get_log()}")

    # __audit_log is name-mangled to _Fund__audit_log
    try:
        _ = f.__audit_log   # type: ignore
    except AttributeError as e:
        print(f"  direct access blocked: {e}")

    # Still accessible via mangled name (for debugging/tests)
    print(f"  mangled access:     {f._Fund__audit_log}")


# ═══════════════════════════════════════════════════════════════════════════════
# Q28  Polymorphism — duck typing + runtime dispatch
# ═══════════════════════════════════════════════════════════════════════════════

def q28_polymorphism() -> None:
    print("\n" + "=" * 60)
    print("Q28  Polymorphism — duck typing and runtime dispatch")
    print("=" * 60)

    # No shared base class needed — duck typing
    class SlackNotifier:
        def notify(self, msg: str) -> str:
            return f"[Slack] {msg}"

    class EmailNotifier:
        def notify(self, msg: str) -> str:
            return f"[Email] {msg}"

    class ServiceNowNotifier:
        def notify(self, msg: str) -> str:
            return f"[ServiceNow P1] {msg}"

    def dispatch_all(notifiers: List[Any], msg: str) -> None:
        for n in notifiers:
            print(f"  {n.notify(msg)}")   # polymorphic call

    dispatch_all(
        [SlackNotifier(), EmailNotifier(), ServiceNowNotifier()],
        "VaR breach detected for FUND-001",
    )

    # singledispatch — explicit runtime dispatch by type
    from functools import singledispatch

    @singledispatch
    def process(data: Any) -> str:
        return f"default: {data!r}"

    @process.register(str)
    def _(data: str) -> str:
        return f"string: {data.upper()}"

    @process.register(list)
    def _(data: list) -> str:
        return f"list of {len(data)} items"

    print(f"  singledispatch str:  {process('hello')}")
    print(f"  singledispatch list: {process([1, 2, 3])}")
    print(f"  singledispatch int:  {process(42)}")


# ═══════════════════════════════════════════════════════════════════════════════
# Q29  Class decorators
# ═══════════════════════════════════════════════════════════════════════════════

def q29_class_decorators() -> None:
    print("\n" + "=" * 60)
    print("Q29  Class decorators")
    print("=" * 60)

    # Class decorator: wrap a class to add behaviour
    def add_repr(cls: type) -> type:
        """Auto-generate __repr__ from all non-private instance attributes."""
        def __repr__(self: Any) -> str:
            attrs = ", ".join(
                f"{k}={v!r}"
                for k, v in vars(self).items()
                if not k.startswith("_")
            )
            return f"{cls.__name__}({attrs})"
        cls.__repr__ = __repr__  # type: ignore[method-assign]
        return cls

    def validate_init(cls: type) -> type:
        """Wrap __init__ to print a validation message."""
        original_init = cls.__init__

        def new_init(self: Any, *args: Any, **kwargs: Any) -> None:
            original_init(self, *args, **kwargs)
            print(f"  [validated] {cls.__name__} created")

        cls.__init__ = new_init  # type: ignore[method-assign]
        return cls

    @add_repr
    @validate_init
    class Threshold:
        def __init__(self, name: str, value: float, unit: str) -> None:
            self.name = name
            self.value = value
            self.unit = unit

    t = Threshold("VaR limit", 0.10, "%")
    print(f"  repr: {t}")


# ═══════════════════════════════════════════════════════════════════════════════
# Q30  Putting it all together — production-style typed pipeline class
# ═══════════════════════════════════════════════════════════════════════════════

def q30_production_pipeline() -> None:
    print("\n" + "=" * 60)
    print("Q30  Production-style typed pipeline (all concepts combined)")
    print("=" * 60)

    T_Result = TypeVar("T_Result")

    @runtime_checkable
    class Runnable(Protocol[T_Result]):
        def run(self) -> T_Result: ...

    @dataclass
    class PipelineConfig:
        fund_id: str
        chunk_size: int = 512
        top_k: int = 5
        dry_run: bool = False

    class PipelineStage(abc.ABC, Generic[T_Result]):
        """Abstract, generic stage with timing."""

        def __init__(self, name: str) -> None:
            self.name = name
            self._metrics: Dict[str, float] = {}

        @abc.abstractmethod
        def execute(self, config: PipelineConfig) -> T_Result: ...

        def run_timed(self, config: PipelineConfig) -> T_Result:
            import time
            start = time.perf_counter()
            result = self.execute(config)
            self._metrics["last_run_ms"] = (time.perf_counter() - start) * 1000
            return result

        def __repr__(self) -> str:
            return f"{self.__class__.__name__}(name={self.name!r})"

    class IngestStage(PipelineStage[List[str]]):
        def execute(self, config: PipelineConfig) -> List[str]:
            # mock — real impl would use SparkEmbeddingPipeline
            return [
                f"chunk_{i} of {config.fund_id}"
                for i in range(3)
            ]

    class EmbedStage(PipelineStage[List[List[float]]]):
        def execute(self, config: PipelineConfig) -> List[List[float]]:
            return [[float(i), float(i + 1)] for i in range(3)]

    class ReviewPipeline:
        """Orchestrates typed stages — composition pattern."""

        def __init__(self, config: PipelineConfig) -> None:
            self.config = config
            self._stages: List[PipelineStage[Any]] = [
                IngestStage("ingest"),
                EmbedStage("embed"),
            ]

        def run(self) -> Dict[str, Any]:
            print(f"  Running pipeline for {self.config.fund_id}")
            results: Dict[str, Any] = {}
            for stage in self._stages:
                result = stage.run_timed(self.config)
                results[stage.name] = result
                ms = stage._metrics.get("last_run_ms", 0)
                print(f"  [{stage.name}] items={len(result)}, time={ms:.2f}ms")
            return results

        def __enter__(self) -> "ReviewPipeline":
            print(f"  [open] pipeline for {self.config.fund_id}")
            return self

        def __exit__(self, *_: Any) -> bool:
            print(f"  [close] pipeline for {self.config.fund_id}")
            return False

    config = PipelineConfig(fund_id="FUND-001", chunk_size=256, top_k=5)
    with ReviewPipeline(config) as pipeline:
        output = pipeline.run()

    print(f"  chunks:  {output['ingest']}")
    print(f"  vectors: {output['embed']}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    demos = [
        q01_class_basics,
        q02_str_vs_repr,
        q03_property,
        q04_classmethod_staticmethod,
        q05_inheritance_super,
        q06_mro,
        q07_isinstance_issubclass,
        q08_operator_overloading,
        q09_slots,
        q10_new_vs_init,
        q11_abc,
        q12_protocol,
        q13_dataclass,
        q14_named_tuple,
        q15_generics,
        q16_type_aliases,
        q17_callable_overload,
        q18_descriptors,
        q19_context_manager,
        q20_iterator_protocol,
        q21_callable_objects,
        q22_metaclasses,
        q23_mixin,
        q24_composition,
        q25_singleton,
        q26_factory,
        q27_encapsulation,
        q28_polymorphism,
        q29_class_decorators,
        q30_production_pipeline,
    ]

    for demo in demos:
        try:
            demo()
        except Exception as e:
            import traceback
            print(f"\n  ERROR in {demo.__name__}: {e}")
            traceback.print_exc()

    print("\n" + "=" * 60)
    print(f"All {len(demos)} OOP & typing questions complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()

