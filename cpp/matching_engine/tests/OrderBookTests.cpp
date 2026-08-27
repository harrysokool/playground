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

TEST(OrderBookCancellationTest, CancelsMiddleOrderAtPriceLevel)
{
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

TEST(OrderBookCancellationTest, PreservesFifoAfterMiddleCancellation)
{
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

TEST(OrderBookCancellationTest, CannotCancelExecutedOrder)
{
    OrderBook book;

    ASSERT_TRUE(book.addOrder(
        Order{1, Side::Sell, 10100, 20}
    ));

    ASSERT_TRUE(book.addOrder(
        Order{2, Side::Buy, 10100, 20}
    ));

    EXPECT_FALSE(book.cancelOrder(1));
}

TEST(OrderBookCancellationTest, AllowsIdReuseAfterCancellation)
{
    OrderBook book;

    ASSERT_TRUE(book.addOrder(
        Order{1, Side::Buy, 10000, 20}
    ));

    ASSERT_TRUE(book.cancelOrder(1));

    EXPECT_TRUE(book.addOrder(
        Order{1, Side::Buy, 9900, 30}
    ));
}