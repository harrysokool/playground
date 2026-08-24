#pragma once

#include "Order.h"
#include "Trade.h"

#include <deque>
#include <functional>
#include <map>
#include <optional>
#include <vector>

class OrderBook {
public:
    void addOrder(const Order& order);
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
    void matchBuyOrder(Order& order);
    void matchSellOrder(Order& order);

    std::map<Price, std::deque<Order>, std::greater<Price>> bids_;
    std::map<Price, std::deque<Order>> asks_;
    std::vector<Trade> trades_;
};