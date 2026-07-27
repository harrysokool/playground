#ifndef PRODUCT_H
#define PRODUCT_H

#include <string>

struct Product {
    int id;
    std::string name;
    int quantity;
    double price;
};

#endif