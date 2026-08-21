#pragma once

#include "Order.h"

class OrderBook {
public:
    void addOrder(const Order& order);
    void printBook() const;
}