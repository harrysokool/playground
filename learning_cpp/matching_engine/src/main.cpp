#include "OrderBook.h"

#include <iostream>

int main() {
    OrderBook orderBook;

    orderBook.addOrder({
        1,
        Side::Buy,
        10100,
        50
    });

    orderBook.addOrder({
        2,
        Side::Buy,
        10000,
        80
    });

    orderBook.addOrder({
        3,
        Side::Sell,
        10200,
        40
    });

    orderBook.printBook();

    if (orderBook.cancelOrder(1)) {
        std::cout << "Order 1 cancelled\n";
    } else {
        std::cout << "Order 1 not found\n";
    }

    orderBook.printBook();

    return 0;
}