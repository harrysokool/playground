#pragma once

#include "Order.h"

#include <deque>
#include <functional>
#include <map>

class OrderBook {
public:
    void addOrder(const Order& order);
    void printBook() const;

private:
    std::map<Price, std::deque<Order>, std::greater<Price>> bids_;
    std::map<Price, std::deque<Order>> asks_;
}