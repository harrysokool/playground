#include "OrderBook.h"

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

    orderBook.addOrder({
        4,
        Side::Sell,
        10300,
        60
    });

    orderBook.addOrder({
        5,
        Side::Buy,
        10100,
        25
    });

    orderBook.printBook();

    return 0;
}