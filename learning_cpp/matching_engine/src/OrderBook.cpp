#include "OrderBook.h"

#include <iomanip>
#include <iostream>

#include <algorithm>


void OrderBook::addOrder(const Order& order) {
    Order incomingOrder = order;

    if (order.side == Side::Buy) {
        matchBuyOrder(incomingOrder);
        
        if (incomingOrder.quantity > 0) {
            bids_[incomingOrder.price].push_back(incomingOrder);
        }
    } else {
        matchSellOrder(incomingOrder);
        
        if (incomingOrder.quantity > 0) {
            asks_[incomingOrder.price].push_back(incomingOrder);
        }
    }
}


bool OrderBook::cancelOrder(OrderId orderId) {
    for (auto priceLevel = bids_.begin(); priceLevel != bids_.end(); ++priceLevel) {
        std::deque<Order>& orders = priceLevel->second;

        for (auto order = orders.begin(); order != orders.end(); ++order) {
            if (order->id == orderId) {
                orders.erase(order);

                if (orders.empty()) {
                    bids_.erase(priceLevel);
                }

                return true;
            }
        }
    }    
    
    for (auto priceLevel = asks_.begin(); priceLevel != asks_.end(); ++priceLevel) {
        std::deque<Order>& orders = priceLevel->second;

        for (auto order = orders.begin(); order != orders.end(); ++order) {
            if (order->id == orderId) {
                orders.erase(order);

                if (orders.empty()) {
                    asks_.erase(priceLevel);
                }

                return true;
            }
        }
    }

    return false;
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

        for (const Order& order: orders) {
            totalQuantity += order.quantity;
        }

        std::cout << "$" << std::fixed << std::setprecision(2)
                    << static_cast<double>(price) / 100.00
                    << " | Quantity: " << totalQuantity
                    << '\n';
    }

    std::cout << "\nBIDS\n";
    for (const auto&[price, orders] : bids_) {
        Quantity totalQuantity = 0;

        for (const Order& order: orders) {
            totalQuantity += order.quantity;
        }

        std::cout << "$" << std::fixed << std::setprecision(2)
                    << static_cast<double>(price) / 100.00
                    << " | Quantity: " << totalQuantity
                    << '\n';
    }
    
    std::cout << "======================================\n";
}


void OrderBook::matchBuyOrder(Order& order) {
    while (order.quantity > 0 && !asks_.empty()) {
        // get the first map entry
        auto bestAsk = asks_.begin();

        // see if the order price match with selling price
        Price askPrice = bestAsk->first;
        if (order.price < askPrice) {
            break;
        }
        
        // get the queue at that price
        std::deque<Order>& ordersAtPrice = bestAsk->second;
        // get the first sell order at that price
        Order& restingOrder = ordersAtPrice.front();

        // trade here
        Quantity tradedQuantity = std::min(order.quantity, restingOrder.quantity);
        order.quantity -= tradedQuantity;
        restingOrder.quantity -= tradedQuantity;
        
        std::cout << "TRADE: "
                    << tradedQuantity
                    << " units at $"
                    << std::fixed
                    << std::setprecision(2)
                    << static_cast<double>(askPrice) / 100.0
                    << '\n';
        
        // after trading, if the sell order is 0, then remove it
        if (restingOrder.quantity == 0) {
            ordersAtPrice.pop_front();
        }

        // if there are no more sell order, then remove that price in the asks_ map
        if (ordersAtPrice.empty()) {
            asks_.erase(bestAsk);
        }
    }
}


void OrderBook::matchSellOrder(Order& order) {
    while (order.quantity > 0 && !bids_.empty()) {
        // get the best bid (highest)
        auto bestBid = bids_.begin();

        // check the price see if it mathces the asking price
        Price bidPrice = bestBid->first;
        if (order.price > bidPrice) {
            break;
        }

        // now we get the queue
        std::deque<Order>& ordersAtPrice = bestBid->second;
        Order& restingOrder = ordersAtPrice.front();

        // now we trade
        Quantity tradedQuantity = std::min(order.quantity, restingOrder.quantity);
        order.quantity -= tradedQuantity;
        restingOrder.quantity -= tradedQuantity;

        std::cout << "TRADE: "
                    << tradedQuantity
                    << " units at $"
                    << std::fixed
                    << std::setprecision(2)
                    << static_cast<double>(bidPrice) / 100.0
                    << '\n';

        if (restingOrder.quantity == 0) {
            ordersAtPrice.pop_front();
        }

        if (ordersAtPrice.empty()) {
            bids_.erase(bestBid);
        }
    }
}


std::optional<Price> OrderBook::bestBid() const {
    if (bids_.empty()){
        return std::nullopt;
    }

    return bids_.begin()->first;
}


std::optional<Price> OrderBook::bestAsk() const {
    if (asks_.empty()) {
        return std::nullopt;
    }

    return asks_.begin()->first;
}


Quantity OrderBook::bidQuantityAt(Price price) const {
    auto priceLevel = bids_.find(price);
    if (priceLevel == bids_.end()) {
        return 0;
    }

    Quantity total = 0;
    for (const Order& order : priceLevel->second) {
        total += order.quantity;
    }

    return total;
}


Quantity OrderBook::askQuantityAt(Price price) const {
    auto priceLevel = asks_.find(price);
    if (priceLevel == asks_.end()) {
        return 0;
    }

    Quantity total = 0;
    for (const Order& order : priceLevel->second) {
        total += order.quantity;
    }

    return total;
}