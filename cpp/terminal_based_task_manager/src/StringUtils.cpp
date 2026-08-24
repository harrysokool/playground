// StringUtils.cpp

#include "StringUtils.h"

std::string lower(std::string str) {
    for (char& c:str) {
        c = static_cast<char>(
            std::tolower(static_cast<unsigned char>(c))
        );
    }

    return str;
}