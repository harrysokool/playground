#include "OrderBook.h"

#include <cassert>
#include <iostream>
#include <gtest/gtest.h>

TEST(OrderBookTest, AddsBuyOrder) {
    OrderBook book;

    bool result = book.addOrder({
        Order{1, Side::Buy, 10000, 50}
    });

    EXPECT_TRUE(result);
    ASSERT_TRUE(book.bestBid().has_value());
    EXPECT_EQ(book.bestBid().value(), 10000);
}

TEST(OrderBookCancellationTest, RemovesOnlyOrderAndPriceLevel) {
    OrderBook book;

    ASSERT_TRUE(book.addOrder({
        Order{1, Side::Buy, 10000, 50}
    }));

    EXPECT_TRUE(book.cancelOrder(1));
    EXPECT_FALSE(book.bestBid().has_value());
    EXPECT_EQ(book.bidQuantityAt(10000), 0);
}

TEST(OrderBookCancellationTest, CancelsMiddleOrderAtPriceLevel) {
    OrderBook book;

    ASSERT_TRUE(book.addOrder(
        Order{1, Side::Buy, 10000, 10}
    ));

    ASSERT_TRUE(book.addOrder(
        Order{2, Side::Buy, 10000, 20}
    ));

    ASSERT_TRUE(book.addOrder(
        Order{3, Side::Buy, 10000, 30}
    ));

    EXPECT_TRUE(book.cancelOrder(2));
    EXPECT_EQ(book.bidQuantityAt(10000), 40);
    EXPECT_EQ(book.firstBidOrderIdAt(10000), 1);
}

TEST(OrderBookCancellationTest, PreservesFifoAfterMiddleCancellation) {
    OrderBook book;

    ASSERT_TRUE(book.addOrder(
        Order{1, Side::Sell, 10100, 10}
    ));

    ASSERT_TRUE(book.addOrder(
        Order{2, Side::Sell, 10100, 10}
    ));

    ASSERT_TRUE(book.addOrder(
        Order{3, Side::Sell, 10100, 10}
    ));

    ASSERT_TRUE(book.cancelOrder(2));

    ASSERT_TRUE(book.addOrder(
        Order{4, Side::Buy, 10100, 20}
    ));

    ASSERT_EQ(book.trades().size(), 2);

    EXPECT_EQ(book.trades()[0].sellOrderId, 1);
    EXPECT_EQ(book.trades()[1].sellOrderId, 3);
}

TEST(OrderBookCancellationTest, CannotCancelExecutedOrder) {
    OrderBook book;

    ASSERT_TRUE(book.addOrder(
        Order{1, Side::Sell, 10100, 20}
    ));

    ASSERT_TRUE(book.addOrder(
        Order{2, Side::Buy, 10100, 20}
    ));

    EXPECT_FALSE(book.cancelOrder(1));
}

TEST(OrderBookCancellationTest, AllowsIdReuseAfterCancellation) {
    OrderBook book;

    ASSERT_TRUE(book.addOrder(
        Order{1, Side::Buy, 10000, 20}
    ));

    ASSERT_TRUE(book.cancelOrder(1));

    EXPECT_TRUE(book.addOrder(
        Order{1, Side::Buy, 9900, 30}
    ));
}

TEST(OrderBookTest, testAddOrders) {
    OrderBook book;
    ASSERT_TRUE(book.addOrder({1, Side::Buy, 10100, 50}));
    ASSERT_TRUE(book.addOrder({2, Side::Sell, 10300, 40}));

    ASSERT_TRUE(book.bestBid().has_value());
    ASSERT_TRUE(book.bestBid().value() == 10100);
    ASSERT_TRUE(book.bidQuantityAt(10100) == 50);

    ASSERT_TRUE(book.bestAsk().has_value());
    ASSERT_TRUE(book.bestAsk().value() == 10300);
    ASSERT_TRUE(book.askQuantityAt(10300) == 40);

}

TEST(OrderBookTest, testAddOrders) {
    OrderBook book;

    book.addOrder({1, Side::Buy, 10100, 50});
    book.addOrder({2, Side::Sell, 10300, 40});

    ASSERT_TRUE(book.bestBid().has_value());
    ASSERT_TRUE(book.bestBid().value() == 10100);
    ASSERT_TRUE(book.bidQuantityAt(10100) == 50);

    ASSERT_TRUE(book.bestAsk().has_value());
    ASSERT_TRUE(book.bestAsk().value() == 10300);
    ASSERT_TRUE(book.askQuantityAt(10300) == 40);
}

TEST(OrderBookTest, testFullFill) {
    OrderBook book;

    book.addOrder({1, Side::Sell, 10200, 50});
    book.addOrder({2, Side::Buy, 10200, 50});

    ASSERT_TRUE(!book.bestBid().has_value());
    ASSERT_TRUE(!book.bestAsk().has_value());
}

TEST(OrderBookTest, testPartialFill) {
    OrderBook book;

    book.addOrder({1, Side::Sell, 10200, 80});
    book.addOrder({2, Side::Buy, 10200, 50});

    ASSERT_TRUE(!book.bestBid().has_value());
    ASSERT_TRUE(book.bestAsk().value() == 10200);
    ASSERT_TRUE(book.askQuantityAt(10200) == 30);
}

TEST(OrderBookTest, testMultiplePriceLevels) {
    OrderBook book;

    book.addOrder({1, Side::Sell, 10100, 30});
    book.addOrder({2, Side::Sell, 10200, 40});
    book.addOrder({3, Side::Sell, 10300, 50});

    book.addOrder({4, Side::Buy, 10200, 60});

    ASSERT_TRUE(book.askQuantityAt(10100) == 0);
    ASSERT_TRUE(book.askQuantityAt(10200) == 10);
    ASSERT_TRUE(book.askQuantityAt(10300) == 50);
    ASSERT_TRUE(book.bestAsk().value() == 10200);
}

TEST(OrderBookTest, testCancellation) {
    OrderBook book;

    book.addOrder({1, Side::Buy, 10100, 50});

    ASSERT_TRUE(book.cancelOrder(1));
    ASSERT_TRUE(!book.bestBid().has_value());
    ASSERT_TRUE(!book.cancelOrder(999));
}

TEST(OrderBookTest, testPriceTimePriority) {
    OrderBook book;

    book.addOrder({1, Side::Sell, 10200, 40});
    book.addOrder({2, Side::Sell, 10200, 50});

    ASSERT_TRUE(book.firstAskOrderIdAt(10200).value() == 1);

    book.addOrder({3, Side::Buy, 10200, 45});

    ASSERT_TRUE(book.askQuantityAt(10200) == 45);
    ASSERT_TRUE(book.firstAskOrderIdAt(10200).value() == 2);
}


TEST(OrderBookTest, testTradeRecord) {
    OrderBook book;

    book.addOrder({1, Side::Sell, 10200, 40});
    book.addOrder({2, Side::Buy, 10300, 25});

    const std::vector<Trade>& trades = book.trades();

    ASSERT_TRUE(trades.size() == 1);

    const Trade& trade = trades.front();

    ASSERT_TRUE(trade.buyOrderId == 2);
    ASSERT_TRUE(trade.sellOrderId == 1);
    ASSERT_TRUE(trade.price == 10200);
    ASSERT_TRUE(trade.quantity == 25);

    ASSERT_TRUE(book.askQuantityAt(10200) == 15);
}

TEST(OrderBookTest, testRejectInvalidOrders) {
    OrderBook book;

    ASSERT_TRUE(!book.addOrder({1, Side::Buy, 0, 50}));
    ASSERT_TRUE(!book.addOrder({2, Side::Buy, 10100, 0}));

    ASSERT_TRUE(!book.bestBid().has_value());
    ASSERT_TRUE(!book.bestAsk().has_value());
}

TEST(OrderBookTest, testRejectDuplicateActiveOrderId) {
    OrderBook book;

    ASSERT_TRUE(book.addOrder({1, Side::Buy, 10100, 50}));
    ASSERT_TRUE(!book.addOrder({1, Side::Sell, 10300, 40}));

    ASSERT_TRUE(book.bidQuantityAt(10100) == 50);
    ASSERT_TRUE(book.askQuantityAt(10300) == 0);
}

TEST(OrderBookTest, testNonCrossingOrders) {
    OrderBook book;

    ASSERT_TRUE(book.addOrder({1, Side::Buy, 10000, 50}));
    ASSERT_TRUE(book.addOrder({2, Side::Sell, 10100, 40}));

    ASSERT_TRUE(book.bestBid().has_value());
    ASSERT_TRUE(book.bestBid().value() == 10000);

    ASSERT_TRUE(book.bestAsk().has_value());
    ASSERT_TRUE(book.bestAsk().value() == 10100);

    ASSERT_TRUE(book.bidQuantityAt(10000) == 50);
    ASSERT_TRUE(book.askQuantityAt(10100) == 40);
    ASSERT_TRUE(book.trades().empty());
}

TEST(OrderBookTest, testIncomingBuyExceedsAvailableLiquidity) {
    OrderBook book;

    ASSERT_TRUE(book.addOrder({1, Side::Sell, 10100, 30}));
    ASSERT_TRUE(book.addOrder({2, Side::Buy, 10100, 50}));

    ASSERT_TRUE(book.bestBid().has_value());
    ASSERT_TRUE(book.bestBid().value() == 10100);
    ASSERT_TRUE(book.bidQuantityAt(10100) == 20);

    ASSERT_TRUE(!book.bestAsk().has_value());

    ASSERT_TRUE(book.trades().size() == 1);

    const Trade& trade = book.trades().front();

    ASSERT_TRUE(trade.buyOrderId == 2);
    ASSERT_TRUE(trade.sellOrderId == 1);
    ASSERT_TRUE(trade.price == 10100);
    ASSERT_TRUE(trade.quantity == 30);
}

TEST(OrderBookTest, testCancellationAfterPartialFill) {
    OrderBook book;

    ASSERT_TRUE(book.addOrder({1, Side::Sell, 10200, 100}));
    ASSERT_TRUE(book.addOrder({2, Side::Buy, 10200, 40}));

    ASSERT_TRUE(book.bestAsk().has_value());
    ASSERT_TRUE(book.bestAsk().value() == 10200);
    ASSERT_TRUE(book.askQuantityAt(10200) == 60);

    ASSERT_TRUE(!book.bestBid().has_value());
    ASSERT_TRUE(book.trades().size() == 1);

    ASSERT_TRUE(book.cancelOrder(1));
    ASSERT_TRUE(!book.bestAsk().has_value());
    ASSERT_TRUE(book.askQuantityAt(10200) == 0);

    // Confirms that order ID 1 was removed from activeOrderIds_.
    ASSERT_TRUE(book.addOrder({1, Side::Sell, 10200, 100}));
    ASSERT_TRUE(book.askQuantityAt(10200) == 100);
}

TEST(OrderBookTest, testOrderIdReusableAfterFullFill) {
    OrderBook book;

    ASSERT_TRUE(book.addOrder({1, Side::Sell, 10200, 50}));
    ASSERT_TRUE(book.addOrder({2, Side::Buy, 10200, 50}));

    ASSERT_TRUE(!book.bestAsk().has_value());
    ASSERT_TRUE(!book.bestBid().has_value());

    ASSERT_TRUE(book.addOrder({1, Side::Buy, 10100, 25}));
    ASSERT_TRUE(book.bidQuantityAt(10100) == 25);
}


