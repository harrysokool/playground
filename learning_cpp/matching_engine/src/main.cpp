#include "OrderBook.h"

int main() {
    OrderBook orderBook;

    orderBook.addOrder({
        1,
        Side::Buy,
        10300,
        40
    });

    orderBook.addOrder({
        2,
        Side::Buy,
        10200,
        50
    });

    orderBook.printBook();

    orderBook.addOrder({
        3,
        Side::Sell,
        10200,
        70
    });

    orderBook.printBook();

    return 0;
}