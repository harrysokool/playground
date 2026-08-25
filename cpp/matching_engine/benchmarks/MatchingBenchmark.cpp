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
        const Side side =
            (i % 2 == 0) ? Side::Buy : Side::Sell;

        const bool accepted = book.addOrder({
            static_cast<OrderId>(i + 1),
            side,
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

    std::cout << "Elapsed time:    "
              << elapsed.count()
              << " seconds\n";

    std::cout << "Throughput:      "
              << ordersPerSecond
              << " orders/second\n";

    return 0;
}