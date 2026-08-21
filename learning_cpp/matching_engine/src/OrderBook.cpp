#include "OrderBook.h"

#include <iostream>

void OrderBook::addOrder(const Order& order) {
    std::cout << "Adding order " << order.id << '\n';
}

void OrderBook::printBook() const {
    std::cout << "Order book is currently empty.\n";
}