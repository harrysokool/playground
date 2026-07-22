#ifndef TASK_MANAGER_H
#define TASK_MANAGER_H

#include "Task.h"

#include <vector>

class TaskManager {
    private:
        std::vector<Task> tasks;

        void addTasks();
        void deleteTask();
        void editTask();
        void displayTasks() const;
        void completeTask();
        void reopenTask();
        void loadTasks();
        void saveTasks() const;

    public:
        run();
};


#endif