#pragma once

#include "Order.h"

#include <deque>
#include <functional>
#include <map>

class OrderBook {
public:
    void addOrder(const Order& order);
    bool cancelOrder(OrderId orderId);
    void printBook() const;

private:
    void matchBuyOrder(Order& order);
    void matchSellOrder(Order& order);

    std::map<Price, std::deque<Order>, std::greater<Price>> bids_;
    std::map<Price, std::deque<Order>> asks_;
};