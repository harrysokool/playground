#pragma once

#include "Order.h"
#include "Trade.h"

#include <deque>
#include <functional>
#include <map>
#include <optional>
#include <vector>
#include <unordered_map>

using orderIterator = std::list<Order>::iterator;

class OrderBook {
public:
    bool addOrder(const Order& order);
    bool cancelOrder(OrderId orderId);
    void printBook() const;

    std::optional<Price> bestBid() const;
    std::optional<Price> bestAsk() const;

    Quantity bidQuantityAt(Price price) const;
    Quantity askQuantityAt(Price price) const;

    std::optional<OrderId> firstBidOrderIdAt(Price price) const;
    std::optional<OrderId> firstAskOrderIdAt(Price price) const;

    const std::vector<Trade>& trades() const;

private:
    // this will store the locatin of the order
    // side is to decide if the order is in bids_ or asks_
    // price is to locate the linked list
    // orderIt is to get the linked list node right away
    struct OrderLocation {
        Side side;
        Price price;
        orderIterator orderIt;
    };

    void matchBuyOrder(Order& order);
    void matchSellOrder(Order& order);

    // we will not be using deque, will use linked list instead
    std::map<Price, std::list<Order>, std::greater<Price>> bids_;
    std::map<Price, std::list<Order>> asks_;
    
    // for faster cancel order
    std::unordered_map<OrderId, OrderLocation> orderIndex_;

    // for recording trades
    std::vector<Trade> trades_;
};