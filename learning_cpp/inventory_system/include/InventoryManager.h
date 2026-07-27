#pragma once

#include "Product.h"

// #include <string>
#include <unordered_map>

class InventoryManager {
    private:
        // <product id, product obj>  
        std::unordered_map<int, Product> products;
        int nextProductId = 1;

    public:
        void run();

};