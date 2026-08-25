#include "OrderBook.h"

#include <cassert>
#include <iostream>

void testAddOrders() {
    OrderBook book;

    book.addOrder({1, Side::Buy, 10100, 50});
    book.addOrder({2, Side::Sell, 10300, 40});

    assert(book.bestBid().has_value());
    assert(book.bestBid().value() == 10100);
    assert(book.bidQuantityAt(10100) == 50);

    assert(book.bestAsk().has_value());
    assert(book.bestAsk().value() == 10300);
    assert(book.askQuantityAt(10300) == 40);
}

void testFullFill() {
    OrderBook book;

    book.addOrder({1, Side::Sell, 10200, 50});
    book.addOrder({2, Side::Buy, 10200, 50});

    assert(!book.bestBid().has_value());
    assert(!book.bestAsk().has_value());
}

void testPartialFill() {
    OrderBook book;

    book.addOrder({1, Side::Sell, 10200, 80});
    book.addOrder({2, Side::Buy, 10200, 50});

    assert(!book.bestBid().has_value());
    assert(book.bestAsk().value() == 10200);
    assert(book.askQuantityAt(10200) == 30);
}

void testMultiplePriceLevels() {
    OrderBook book;

    book.addOrder({1, Side::Sell, 10100, 30});
    book.addOrder({2, Side::Sell, 10200, 40});
    book.addOrder({3, Side::Sell, 10300, 50});

    book.addOrder({4, Side::Buy, 10200, 60});

    assert(book.askQuantityAt(10100) == 0);
    assert(book.askQuantityAt(10200) == 10);
    assert(book.askQuantityAt(10300) == 50);
    assert(book.bestAsk().value() == 10200);
}

void testCancellation() {
    OrderBook book;

    book.addOrder({1, Side::Buy, 10100, 50});

    assert(book.cancelOrder(1));
    assert(!book.bestBid().has_value());
    assert(!book.cancelOrder(999));
}

void testPriceTimePriority() {
    OrderBook book;

    book.addOrder({1, Side::Sell, 10200, 40});
    book.addOrder({2, Side::Sell, 10200, 50});

    assert(book.firstAskOrderIdAt(10200).value() == 1);

    book.addOrder({3, Side::Buy, 10200, 45});

    assert(book.askQuantityAt(10200) == 45);
    assert(book.firstAskOrderIdAt(10200).value() == 2);
}


void testTradeRecord() {
    OrderBook book;

    book.addOrder({1, Side::Sell, 10200, 40});
    book.addOrder({2, Side::Buy, 10300, 25});

    const std::vector<Trade>& trades = book.trades();

    assert(trades.size() == 1);

    const Trade& trade = trades.front();

    assert(trade.buyOrderId == 2);
    assert(trade.sellOrderId == 1);
    assert(trade.price == 10200);
    assert(trade.quantity == 25);

    assert(book.askQuantityAt(10200) == 15);
}

void testRejectInvalidOrders() {
    OrderBook book;

    assert(!book.addOrder({1, Side::Buy, 0, 50}));
    assert(!book.addOrder({2, Side::Buy, 10100, 0}));

    assert(!book.bestBid().has_value());
    assert(!book.bestAsk().has_value());
}

void testRejectDuplicateActiveOrderId() {
    OrderBook book;

    assert(book.addOrder({1, Side::Buy, 10100, 50}));
    assert(!book.addOrder({1, Side::Sell, 10300, 40}));

    assert(book.bidQuantityAt(10100) == 50);
    assert(book.askQuantityAt(10300) == 0);
}


int main() {
    testAddOrders();
    testFullFill();
    testPartialFill();
    testMultiplePriceLevels();
    testCancellation();
    testPriceTimePriority();
    testTradeRecord();
    testRejectInvalidOrders();
    testRejectDuplicateActiveOrderId();

    std::cout << "All tests passed.\n";
    return 0;
}

