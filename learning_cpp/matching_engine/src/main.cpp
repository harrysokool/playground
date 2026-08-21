#include "OrderBook.h"

int main() {
    OrderBook orderBook;

    Order order {
        1, 
        Side::Buy,
        10125, 
        100
    };

    orderBook.addOrder(order);
    orderBook.printBook();

    return 0;
}