#include "OrderBook.h"

#include <iomanip>
#include <iostream>
#include <algorithm>


bool OrderBook::addOrder(const Order& order) {
    // safety check for ther order
    if (order.price <= 0 || order.quantity == 0) {
        return false;
    }

    // see if the order exist or not
    if (orderIndex_.find(order.id) != orderIndex_.end()) {
        return false;
    }

    Order incomingOrder = order;

    if (order.side == Side::Buy) {
        matchBuyOrder(incomingOrder);
        
        if (incomingOrder.quantity > 0) {
            std::list<Order>& priceLevel = bids_[incomingOrder.price];
            priceLevel.push_back(incomingOrder);

            OrderLocation orderLoc;
            orderLoc.side = incomingOrder.side;
            orderLoc.price = incomingOrder.price;
            orderLoc.orderIt = std::prev(priceLevel.end());

            orderIndex_[incomingOrder.id] = orderLoc;
        }
    } else {
        matchSellOrder(incomingOrder);
        
        if (incomingOrder.quantity > 0) {
            std::list<Order>& priceLevel = asks_[incomingOrder.price];
            priceLevel.push_back(incomingOrder);

            OrderLocation orderLoc;
            orderLoc.side = incomingOrder.side;
            orderLoc.price = incomingOrder.price;
            orderLoc.orderIt = std::prev(priceLevel.end());

            orderIndex_[incomingOrder.id] = orderLoc;
        }
    }

    return true;
}


bool OrderBook::cancelOrder(OrderId orderId) {
    // first get the struct with the order id
    auto it = orderIndex_.find(orderId);
    if (it == orderIndex_.end()) {
        return false;
    }
    const OrderLocation& orderLoc = it->second;

    if (orderLoc.side == Side::Buy) {
        auto priceLevel = bids_.find(orderLoc.price);
        if (priceLevel == bids_.end()) {
            return false;
        }

        std::list<Order>& orders = priceLevel->second;

        orders.erase(orderLoc.orderIt);
        orderIndex_.erase(orderId);
        if (orders.empty()) {
            bids_.erase(priceLevel);
        }

        return true;
    } else {
        auto priceLevel = asks_.find(orderLoc.price);
        if (priceLevel == asks_.end()) {
            return false;
        }

        std::list<Order>& orders = priceLevel->second;
    
        orders.erase(orderLoc.orderIt);
        orderIndex_.erase(orderId);
        if (orders.empty()) {
            asks_.erase(priceLevel);
        }

        return true;
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
        
        // get the list at that price
        std::list<Order>& ordersAtPrice = bestAsk->second;
        // get the first sell order at that price
        Order& restingOrder = ordersAtPrice.front();

        // trade here
        Quantity tradedQuantity = std::min(order.quantity, restingOrder.quantity);
        order.quantity -= tradedQuantity;
        restingOrder.quantity -= tradedQuantity;
        
        trades_.push_back({
            order.id,
            restingOrder.id,
            askPrice,
            tradedQuantity
        });
        
        // after trading, if the sell order is 0, then remove it
        if (restingOrder.quantity == 0) {
            orderIndex_.erase(restingOrder.id);
            ordersAtPrice.pop_front();
        }

        // if there are no more sell order, then remove that price in the asks_
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

        // now we get the list
        std::list<Order>& ordersAtPrice = bestBid->second;
        Order& restingOrder = ordersAtPrice.front();

        // now we trade
        Quantity tradedQuantity = std::min(order.quantity, restingOrder.quantity);
        order.quantity -= tradedQuantity;
        restingOrder.quantity -= tradedQuantity;

        trades_.push_back({
            restingOrder.id,
            order.id,
            bidPrice,
            tradedQuantity
        });

        if (restingOrder.quantity == 0) {
            orderIndex_.erase(restingOrder.id);
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


std::optional<OrderId> OrderBook::firstBidOrderIdAt(Price price) const {
    auto priceLevel = bids_.find(price);
    if (priceLevel == bids_.end() || priceLevel->second.empty()) {
        return std::nullopt;
    }

    return priceLevel->second.front().id;
}


std::optional<OrderId> OrderBook::firstAskOrderIdAt(Price price) const {
    auto priceLevel = asks_.find(price);
    if (priceLevel == asks_.end() || priceLevel->second.empty()) {
        return std::nullopt;
    }

    return priceLevel->second.front().id;
}


const std::vector<Trade>& OrderBook::trades() const {
    return trades_;
}