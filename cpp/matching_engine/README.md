# C++ Limit Order Matching Engine

A single-threaded limit order matching engine built in C++17. The project models a limit order book, matches buy and sell orders using price-time priority, records trades, validates incoming orders, and supports indexed order cancellation.

## Features

- Buy and sell limit orders
- Price-time priority
- Full and partial fills
- Matching across multiple price levels
- FIFO ordering for orders at the same price
- Order cancellation by ID
- Structured trade records
- Invalid price and quantity rejection
- Duplicate active order ID rejection
- Order ID reuse after cancellation or complete execution
- Automated tests for matching, cancellation, validation, and priority rules
- Deterministic throughput benchmark

## Matching Rules

### Price priority

- Buy orders with higher prices receive priority.
- Sell orders with lower prices receive priority.

### Time priority

Orders at the same price are processed in arrival order. Each price level stores its orders in a FIFO queue.

### Crossing conditions

An incoming buy order can match when:

```text
buy price >= best ask price
```

An incoming sell order can match when:

```text
sell price <= best bid price
```

Trades execute at the resting order's price.

## Example

Assume the order book contains:

```text
SELL 40 units at $102.00
SELL 50 units at $103.00
```

An incoming order requests:

```text
BUY 70 units at $103.00
```

The engine executes:

```text
40 units at $102.00
30 units at $103.00
```

The second sell order remains in the book with 20 units.

## Data Structures

### Price levels

The bid and ask books use ordered maps:

```cpp
std::map<Price, std::deque<Order>, std::greater<Price>> bids_;
std::map<Price, std::deque<Order>> asks_;
```

- `bids_` is ordered from highest to lowest price.
- `asks_` is ordered from lowest to highest price.
- Each price level stores orders in a `std::deque` to preserve FIFO ordering.

### Prices

Prices are stored as integers rather than floating-point values. For example:

```text
$101.25 -> 10125
```

This avoids floating-point comparison and rounding issues.

### Order index

Active orders are indexed by order ID:

```cpp
OrderId -> { side, price }
```

The index identifies the correct side and price level without scanning the entire order book. Cancellation still searches within the selected price-level queue, so it is not fully constant-time.

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
├── .gitignore
├── CMakeLists.txt
└── README.md
```

## Requirements

- C++17-compatible compiler
- CMake 3.16 or later

## Build

Configure and build the project:

```bash
cmake -S . -B build
cmake --build build
```

Run the main executable:

```bash
./build/matching_engine
```

## Tests

Build and run the test executable:

```bash
cmake -S . -B build
cmake --build build
./build/order_book_tests
```

The tests cover:

- Adding bids and asks
- Full fills
- Partial fills
- Matching across multiple price levels
- Price-time priority
- Non-crossing orders
- Trade record generation
- Cancellation
- Cancellation after a partial fill
- Invalid orders
- Duplicate active order IDs
- Order ID reuse

## Benchmark

Configure and build an optimized Release version:

```bash
cmake -S . -B build-release -DCMAKE_BUILD_TYPE=Release
cmake --build build-release
./build-release/matching_benchmark
```

The initial deterministic benchmark submits alternating buy and sell orders at the same price. This represents a best-case full-fill workload because the order book remains small. More realistic growing-book, mixed-operation, and cancellation benchmarks are planned.

## Complexity

Let:

- `P` be the number of price levels
- `K` be the number of orders at a selected price level
- `M` be the number of orders or price levels consumed by a match

Key operations have the following approximate costs:

- Best bid or ask lookup: `O(1)` using the beginning of the ordered map
- New price-level insertion: `O(log P)`
- Adding to an existing price level: `O(log P)` map lookup, followed by constant-time insertion at the back of the deque
- Matching: proportional to the number of resting orders and price levels consumed
- Indexed order lookup: average `O(1)` using an unordered map
- Cancellation: average `O(1)` index lookup, `O(log P)` price-level lookup, and `O(K)` search and removal within that level

## Design Decisions

### Why is the engine single-threaded?

Order matching is processed sequentially to preserve deterministic price-time priority. Concurrency can be added around the engine, such as at the order-entry or market-data layers, without making the core matching sequence nondeterministic.

### Why use separate buy and sell matching functions?

Buy and sell orders use opposite books and price comparisons. Separate functions keep these rules explicit and easier to test.

### Why return structured trades?

Trade records separate matching logic from presentation. Tests and future system components can inspect executions without parsing console output.

## Current Limitations

- Supports limit orders only
- Supports one order book rather than multiple symbols
- Cancellation still performs a linear search within one price level
- Uses basic `assert()`-based tests rather than a dedicated testing framework
- Does not persist orders or trades
- Does not provide a network interface
- The initial benchmark represents a best-case workload

## Planned Improvements

- Add randomized invariant and stress tests
- Run AddressSanitizer and UndefinedBehaviorSanitizer
- Adopt GoogleTest or Catch2
- Add GitHub Actions for automated builds and tests
- Expand benchmarks to growing-book, cancellation, and mixed workloads
- Evaluate stable iterators for faster cancellation
- Support multiple instruments in a future exchange simulator

## Purpose

This project was built to study modern C++ data structures, order-book mechanics, matching algorithms, iterator safety, testing, and performance measurement. It is an educational implementation and is not intended for production trading.
