#include "OrderBook.h"

#include <iostream>

void OrderBook::addOrder(const Order& order) {
    if (order.side == Side::Buy) {
        bids_[order.price].push_back(order);
    } else {
        asks_[order.price].push_back(order);
    }
}
/*
    BIDS
    $101.00: 50
    $100.00: 80
     
    ASKS
    $102.00: 40
    $103.00: 60
*/
void OrderBook::printBook() const {
    std::cout << "==============Order Book==============\n";
    std::cout << "\nASKS\n";
    for (const auto&[price, orders] : asks_) {
        Quantity totalQuantity = 0;

        for (const auto& order: orders) {
            totalQuantity += order.quantity;
        }

        std::cout << "$" << std::fixed << std::setprecision(2)
                    << static_cast<double>(price) / 100.00
                    << " | Quantity: " << totalQuantity
                    << '\n';
    }

    std::cout << "\nBIDS\n";
    for (const auto&[price, orders] : asks_) {
        Quantity totalQuantity = 0;

        for (const auto& order: orders) {
            totalQuantity += order.quantity;
        }

        std::cout << "$" << std::fixed << std::setprecision(2)
                    << static_cast<double>(price) / 100.00
                    << " | Quantity: " << totalQuantity
                    << '\n';
    }
    
    std::cout << "==============Order Book==============\n";
}