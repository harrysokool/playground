#ifndef TASK_H
#define TASK_H

#include <string>

enum class Priority {
    Low, 
    Medium, 
    High
};

struct Task {
    int id;
    std::string title;
    std::string description = "";
    Priority priority = Priority::Medium;
    bool completed = false;
};

#endif