#include "OrderBook.h"

int main() {
    OrderBook orderBook;

    orderBook.addOrder({
        1,
        Side::Sell,
        10200,
        40
    });

    orderBook.addOrder({
        2,
        Side::Sell,
        10300,
        50
    });

    orderBook.printBook();

    orderBook.addOrder({
        3,
        Side::Buy,
        10300,
        70
    });

    orderBook.printBook();

    return 0;
}