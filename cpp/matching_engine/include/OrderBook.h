#pragma once

#include "Order.h"
#include "Trade.h"

#include <deque>
#include <functional>
#include <map>
#include <optional>
#include <vector>
#include <unordered_set>
#include <unordered_map>

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
    struct OrderLocation {
        Side side;
        Price price;
    };

    void matchBuyOrder(Order& order);
    void matchSellOrder(Order& order);

    std::map<Price, std::deque<Order>, std::greater<Price>> bids_;
    std::map<Price, std::deque<Order>> asks_;
    
    std::unordered_set<OrderId> activeOrderIds_;
    // for faster cancel order
    std::unordered_map<Orderid, OrderLocation> orderIndex_;

    // for recording trades
    std::vector<Trade> trades_;
};