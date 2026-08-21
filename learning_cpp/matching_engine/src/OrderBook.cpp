#include "OrderBook.h"

#include <iostream>

void OrderBook::addOrder(const Order& order) {
    if (order.side == Side::Buy) {
        bids_[order.price].push_back(order);
    } else {
        asks_[order.price].push_back(order);
    }
}

void OrderBook::printBook() const {
    std::cout << "==============Order Book==============\n";
}