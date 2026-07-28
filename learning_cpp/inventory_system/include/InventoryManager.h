#pragma once

#include "Product.h"

#include <string>
#include <unordered_map>

class InventoryManager {
    private:
        // ATTR
        std::unordered_map<int, Product> products; // <product id, product obj>  
        int nextProductId = 1;

        // FUNC
        void addProducts();           // allow user to add 1-10 products one time
        void deleteProduct();         // delete 1 product by id
        void updateProduct();         // update 1 product by id
        void displayProducts() const; // display all products
        void displayProduct(const Product& product) const; // only showing 1 product
        void findProduct() const;
        const Product* findProduct(int id) const;     // find 1 product by id
        void saveProducts() const;
        void loadProducts();
        bool readInteger(const std::string& prompt, int& value);
        bool readInteger(const std::string& prompt, int& value, int minimum, int maximum);
        bool readDouble(const std::string& prompt, double& value);


    public:
        void run();
};