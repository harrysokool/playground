# C++ Limit Order Matching Engine

A single-threaded limit order matching engine built in C++17.

It maintains a limit order book, matches orders using price-time priority, records trades, validates incoming orders, and supports indexed cancellation using stable list iterators.

## Features

- Buy and sell limit orders
- Price-time priority
- Full and partial fills
- Matching across multiple price levels
- FIFO ordering at the same price
- Indexed order cancellation
- Structured trade records
- Input validation and duplicate ID rejection
- Order ID reuse after cancellation or execution
- GoogleTest test suite
- Deterministic throughput benchmark
- Optional AddressSanitizer and UndefinedBehaviorSanitizer support

## Matching Rules

- Higher-priced buy orders receive priority.
- Lower-priced sell orders receive priority.
- Orders at the same price are matched in arrival order.
- Trades execute at the resting order's price.

An incoming buy order can match when:

```text
buy price >= best ask price
```

An incoming sell order can match when:

```text
sell price <= best bid price
```

## Example

Order book:

```text
SELL 40 units at $102.00
SELL 50 units at $103.00
```

Incoming order:

```text
BUY 70 units at $103.00
```

Executions:

```text
40 units at $102.00
30 units at $103.00
```

The second sell order remains with 20 units.

## Data Structures

Price levels are stored in ordered maps:

```cpp
std::map<Price, std::list<Order>, std::greater<Price>> bids_;
std::map<Price, std::list<Order>> asks_;
```

Each price level uses a list to preserve FIFO order and provide stable iterators.

Active orders are indexed by ID:

```cpp
OrderId -> { side, price, list iterator }
```

This allows an order to be removed directly from its price-level list without scanning through every order at that price.

Prices are stored as integers to avoid floating-point issues:

```text
$101.25 -> 10125
```

## Project Structure

```text
matching_engine/
├── benchmarks/
│   └── MatchingBenchmark.cpp
├── include/
│   ├── Order.h
│   ├── OrderBook.h
│   └── Trade.h
├── src/
│   ├── main.cpp
│   └── OrderBook.cpp
├── tests/
│   └── OrderBookTests.cpp
├── CMakeLists.txt
└── README.md
```

## Build

Requirements:

- C++17-compatible compiler
- CMake 3.16 or later

```bash
cmake -S . -B build
cmake --build build
./build/matching_engine
```

## Tests

The project uses GoogleTest.

```bash
cmake -S . -B build
cmake --build build
ctest --test-dir build --output-on-failure
```

The tests cover matching, partial fills, price-time priority, cancellation, validation, trade generation, and order ID reuse.

## Sanitizers

Run the tests with AddressSanitizer and UndefinedBehaviorSanitizer:

```bash
cmake -S . -B build-sanitized -DENABLE_SANITIZERS=ON
cmake --build build-sanitized
ctest --test-dir build-sanitized --output-on-failure
```

## Benchmark

Build and run the optimized benchmark:

```bash
cmake -S . -B build-release -DCMAKE_BUILD_TYPE=Release
cmake --build build-release
./build-release/matching_benchmark
```

The current benchmark uses a deterministic full-fill workload. More realistic growing-book, cancellation-heavy, and mixed-operation benchmarks are planned.

## Complexity

Let `P` be the number of active price levels.

- Best bid or ask lookup: `O(1)`
- Price-level insertion or lookup: `O(log P)`
- Insert order into an existing level: `O(1)`
- Remove order using a stored list iterator: `O(1)`
- Indexed order lookup: average `O(1)`
- Cancellation: average `O(1)` index lookup, `O(log P)` price-level lookup, and `O(1)` list removal
- Matching: proportional to the number of resting orders consumed

## Current Limitations

- Limit orders only
- Single instrument
- Single-threaded
- No persistence or network interface
- Uses standard-library containers rather than specialized low-latency structures
- Initial benchmark represents a best-case workload

## Planned Improvements

- Add GitHub Actions
- Add randomized invariant tests
- Expand benchmark workloads
- Add market and immediate-or-cancel orders
- Support multiple instruments

## Purpose

This is an educational project for learning modern C++, STL containers, order-book mechanics, iterator safety, testing, and performance measurement.

It is not intended for production trading.
