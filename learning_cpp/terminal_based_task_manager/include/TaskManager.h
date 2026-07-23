#ifndef TASK_MANAGER_H
#define TASK_MANAGER_H

#include "Task.h"

#include <string>
#include <vector>

class TaskManager {
    private:
        std::vector<Task> tasks;
        int nextTaskId = 1;

        void addTasks();
        void deleteTask();
        void editTask();
        void displayTasks() const;
        void completeTask();
        void reopenTask();
        void loadTasks();
        void saveTasks() const;
        bool hasNoTasks() const;
        std::string priorityToString(Priority priority) const;
        Priority stringToPriority(const std::string& priority) const;

    public:
        void run();
};


#endif