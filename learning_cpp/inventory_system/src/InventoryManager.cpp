#include "InventoryManager.h"
#include "StringUtils.h"

#include <string>
#include <iostream>
#include <algorithm>
#include <fstream>
#include <algorithm>

#include <nlohmann/json.hpp>

void InventoryManager::run() {
    loadProducts();

    while (true) {
        int choiceNo;

        if (!readInteger(
                "\n===== Inventory Manager =====\n"
                "1. Add products\n"
                "2. Display product\n"
                "3. Delete product\n"
                "4. Edit product\n"
                "5. Find product\n"
                "6. <placeholder>\n"
                "7. Exit\n"
                "Enter your choice: ",
                choiceNo,
                1,
                7)) 
        {
            continue;
        }

        switch (choiceNo) {
            case 1:
                addProducts();
                break;
            case 2:
                displayProducts();
                break;
            case 3:
                deleteProduct();
                break;
            case 4:
                updateProduct();
                break;
            case 5:
                findProduct();
                break;
            case 6:
                break;
            case 7:
                saveProducts();
                std::cout << "Goodbye!\n";
                return;
        }
    }
}

void InventoryManager::addProducts() {
    // first ask how many products user wants to add
    int productCount;
    if (!readInteger(
        "How many products you wish to add? (1-10)",
        productCount,
        1,
        10
    )) 
    {
        std::cout << "Enter number between 1-10";
        return;
    }

    for (int i=0; i < productCount; i++) {
        Product product;

        // name
        std::cout << "Enter product name: ";
        std::getline(std::cin, product.name);

        if (product.name.empty()) {
            std::cout << "Product name cannot be empty.\n";
            --i;
            continue;
        }

        // quantity
        int quantity;
        if (!readInteger(
            "Enter product quantity: ",
            quantity
        )) {
            std::cout << "Invalid quantity entered.\n";
            --i;
            continue;
        }

        if (quantity < 0) {
            std::cout << "invalid quantity entered.\n";
            --i;
            continue;
        }
        product.quantity = quantity;
        
        // price
        double price;
        if (!readInteger(
            "Enter product price: ",
            price
        )) {
            std::cout << "Invalid price entered.\n";
            --i;
            continue;
        }
        
        if (price < 0) {
            std::cout << "invalid price entered.\n";
            --i;
            continue;
        }
        product.price = price;
        product.id = nextProductId++;

        products[product.id] = product;
    }

    displayProducts();
}

void InventoryManager::deleteProduct() {
    
}

void InventoryManager::updateProduct() {
    
}

void InventoryManager::displayProducts() {
    
}

void InventoryManager::findProduct() {
    
}

void InventoryManager::saveProducts() {
    
}

void InventoryManager::loadProducts() {
    
}

bool TaskManager::readInteger(const std::string& prompt, int& value) {
    std::cout << prompt;

    if (!(std::cin >> value)) {
        std::cout << "Please enter a valid number.\n";
        std::cin.clear();
        std::cin.ignore(
            std::numeric_limits<std::streamsize>::max(),
            '\n'
        );
        return false;
    }

    std::cin.ignore(
        std::numeric_limits<std::streamsize>::max(),
        '\n'
    );

    return true;
}

bool TaskManager::readInteger(
    const std::string& prompt,
    int& value,
    int minimum,
    int maximum
) {
    if (!readInteger(prompt, value)) {
        return false;
    }

    if (value < minimum || value > maximum) {
        std::cout << "Please enter a number between "
                  << minimum << " and "
                  << maximum << ".\n";
        return false;
    }

    return true;
}