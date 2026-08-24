#pragma once

#include <cstdint>

using OrderId = std::uint64_t;
using Price = std::uint64_t;
using Quantity = std::uint64_t;

enum class Side {
    Buy, 
    Sell,
};

struct Order {
    OrderId id;
    Side side;
    Price price;
    Quantity quantity;
};