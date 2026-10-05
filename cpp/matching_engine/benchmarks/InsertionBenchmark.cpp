#include "OrderBook.h"

#include <chrono>
#include <cstddef>
#include <iomanip>
#include <iostream>

int main() {
    constexpr std::size_t ORDER_COUNT = 100000;
    constexpr Price PRICE = 10000;
    constexpr Quantity QUANTITY = 100;

    OrderBook book;
    std::size_t acceptedOrders = 0;

    const auto start = std::chrono::steady_clock::now();

    for (std::size_t i = 0; i < ORDER_COUNT; ++i) {
        const bool accepted = book.addOrder({
            static_cast<OrderId>(i + 1),
            Side::Buy,
            PRICE,
            QUANTITY
        });

        if (accepted) {
            ++acceptedOrders;
        }
    }

    const auto end = std::chrono::steady_clock::now();

    const std::chrono::duration<double> elapsed = end - start;

    const double ordersPerSecond =
        static_cast<double>(acceptedOrders) / elapsed.count();

    const double nanosecondsPerOrder = 
        elapsed.count() * 1'000'000'000.0 / static_cast<double>(acceptedOrders);

    const Quantity expectedQuantity = static_cast<Quantity>(ORDER_COUNT) * QUANTITY;

    std::cout << std::fixed << std::setprecision(3);

    std::cout << "Orders submitted: "
              << ORDER_COUNT
              << '\n';

    std::cout << "Orders accepted:  "
              << acceptedOrders
              << '\n';

    std::cout << "Trades executed: "
              << book.trades().size()
              << '\n';

    std::cout << "Elapsed time: "
              << elapsed.count()
              << " seconds\n";

    std::cout << "Throughput: "
              << ordersPerSecond
              << " orders/second\n";

    std::cout << "Average latency: "
              << nanosecondsPerOrder
              << " ns/order\n";

    std::cout << "Expected quantity: " << expectedQuantity << '\n'; 
    std::cout << "Actual quantity: " << book.bidQuantityAt(PRICE) << '\n';

    return 0;
}