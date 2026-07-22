#ifndef TASK_H
#define TASK_H

#include <string>

struct Task {
    std::string title;
    std::string description = "";
    bool completed = false;
};

#endif