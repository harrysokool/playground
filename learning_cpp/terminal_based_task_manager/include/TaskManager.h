#ifndef TASK_MANAGER_H
#define TASK_MANAGER_H

#include "Task.h"

#include <string>
#include <vector>

class TaskManager {
    private:
        std::vector<Task> tasks;
        int nextTaskId = 0;

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
        Task* findTaskById(int id);
        bool readInteger(const std::string& prompt, int& value);
        bool readInteger(const std::string& prompt, int& value, int min, int max);

    public:
        void run();
};


#endif