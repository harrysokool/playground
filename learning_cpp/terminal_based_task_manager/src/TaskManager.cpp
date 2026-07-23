#include "TaskManager.h"

#include <fstream>
#include <iostream>
#include <limits>
#include <string>
#include <algorithm>


void TaskManager::run() {
    loadTasks();

    while (true){
        int choiceNo;
        
        // display options
        std::cout << "\n===== Task Manager =====\n" 
            << "1. Add tasks \n"
            << "2. Display tasks \n"
            << "3. Delete task \n"
            << "4. Complete a task \n"
            << "5. Edit task\n"
            << "6. Reopen task\n"
            << "7. Exit \n"
            << "Enter your choice: ";
        
        // check user input
        if (!(std::cin >> choiceNo)) {
            std::cout << "Please enter a number.\n";

            std::cin.clear();
            std::cin.ignore(
                std::numeric_limits<std::streamsize>::max(),
                '\n'
            );
            continue;
        }
        
        switch (choiceNo) {
            case 1:
                addTasks();
                break;
            case 2:
                displayTasks();
                break;
            case 3:
                deleteTask();
                break;
            case 4:
                completeTask();
                break;
            case 5:
                editTask();
                break;
            case 6:
                reopenTask();
                break;
            case 7:
                saveTasks();
                std::cout << "Goodbye!" << std::endl;
                return;
            default:
                std::cout << "Invalid option. Please enter a number from 1 to 7.\n";
                break;
        }
    }
}

void TaskManager::addTasks() {
    int taskCount = 0;
    std::cout << "How many tasks do you want to complete today? ";

    if (!(std::cin >> taskCount)) {
        std::cout << "Please enter a number.\n";

        std::cin.clear();
        std::cin.ignore(
            std::numeric_limits<std::streamsize>::max(),
            '\n'
        );
        return;
    }

    // allow only adding between 1-10 tasks
    if (taskCount < 1 || taskCount > 10) {
        std::cout << "Please enter a number between 1 and 10.\n";
        return;
    }

    std::cin.ignore(
        std::numeric_limits<std::streamsize>::max(),
        '\n'
    );

    for (int i = 1; i <= taskCount; ++i) {
        Task task;

        std::cout << "Task" << i << ": \n";
        std::cout << "Task Title: ";
        std::getline(std::cin, task.title);

        std::cout << "Task Description: ";
        std::getline(std::cin, task.description);

        int priorityChoice;
        std::cout << "Priority:\n"
                    << "1. Low\n"
                    << "2. Medium\n"
                    << "3. High\n"
                    << "Enter priority: ";

        if (!(std::cin >> priorityChoice)) {
            std::cout << "Please enter a number!\n";
            std::cin.clear();
            std::cin.ignore(
                std::numeric_limits<std::streamsize>::max(),
                '\n'
            );
            return;
        }

        switch (priorityChoice) {
            case 1:
                task.priority = Priority::Low;
                break;
            case 2:
                task.priority = Priority::Medium;
                break;
            case 3:
                task.priority = Priority::High;
                break;
            default:
                std::cout << "Invalid priority. Using Medium.\n";
                task.priority = Priority::Medium;

        }
        
        task.id = nextTaskId++;
        tasks.push_back(task);
    }
}

// Todo: use id instead of idx
void TaskManager::deleteTask() {
    if (hasNoTasks()) return;

    displayTasks();

    int idx;
    std::cout << "Enter Task number to remove: ";

    if (!(std::cin >> idx)) {
        std::cout << "Please enter a number.\n";

        std::cin.clear();
        std::cin.ignore(
            std::numeric_limits<std::streamsize>::max(),
            '\n'
        );
        return;
    }
    
    if (idx <= 0 || idx > static_cast<int>(tasks.size())) {
        std::cout << "Not a valid option";
        return;
    }

    tasks.erase(tasks.begin() + idx-1);
    std::cout << "Task removed. \n";

    displayTasks();
}

// Todo: use id instead of idx
void TaskManager::editTask() {
    if (hasNoTasks()) return;

    displayTasks();

    int idx;
    std::cout << "Enter task number to edit: ";

    if (!(std::cin >> idx)) {
        std::cout << "Please enter a number.\n";

        std::cin.clear();
        std::cin.ignore(
            std::numeric_limits<std::streamsize>::max(),
            '\n'
        );
        return;
    }

    if (idx <= 0 || idx > static_cast<int>(tasks.size())) {
        std::cout << "Task number does not exist!";
        return;
    }

    std::cin.ignore(
        std::numeric_limits<std::streamsize>::max(),
        '\n'
    );

    std::cout << "New title: ";
    std::string newTitle;
    std::getline(std::cin, newTitle);

    if (newTitle.empty()) {
        std::cout << "Task title cannot be empty.\n";
        return;
    }

    tasks[idx-1].title = newTitle;

    std::cout << "New Description: ";
    std::string newDescription;
    std::getline(std::cin, newDescription);

    if (newDescription.empty()) {
        std::cout << "New task description is empty, so not updated.";
        return;
    }

    tasks[idx-1].description = newDescription;

    std::cout << "Task updated successfully.\n";
    displayTasks();
}

void TaskManager::displayTasks() const {
    if (hasNoTasks()) return;

    std::cout << "\nThese are your tasks:\n";

    for (std::size_t i = 0; i < tasks.size(); ++i) {
        std::cout << "ID " << tasks[i].id << ": "
                  << (tasks[i].completed ? "[x] " : "[ ] ")
                  << tasks[i].title
                  << " | Priority: "
                  << priorityToString(tasks[i].priority)
                  << '\n';
                  << tasks[i].description
    }
}

// Todo: use id instead of idx
void TaskManager::completeTask() {
    if (hasNoTasks()) return;

    displayTasks();

    int idx;
    std::cout << "Enter task number to be mark completed: ";

    if (!(std::cin >> idx)) {
        std::cout << "Please enter a number.\n";

        std::cin.clear();
        std::cin.ignore(
            std::numeric_limits<std::streamsize>::max(),
            '\n'
        );
        return;
    }

    if (idx <= 0 || idx > static_cast<int>(tasks.size())) {
        std::cout << "GET OUT";
        return;
    }

    tasks[idx-1].completed = true;

    displayTasks();
}

// Todo: use id instead of idx
void TaskManager::reopenTask() {
    if (hasNoTasks()) return;

    displayTasks();

    int idx;
    std::cout << "Enter Task number to reopen: ";

    if (!(std::cin >> idx)) {
        std::cout << "Please enter a number.\n";

        std::cin.clear();
        std::cin.ignore(
            std::numeric_limits<std::streamsize>::max(),
            '\n'
        );
        return;
    }

    if (idx <= 0 || idx > static_cast<int>(tasks.size())) {
        std::cout << "Please enter a valid task number.";
        return;
    }

    if (!tasks[idx-1].completed) {
        std::cout << "Task is incomplete, so cannot reopen";
        return;
    }

    tasks[idx-1].completed = false;

    std::cout << "Task reopened successfully.\n";
    displayTasks();
}

void TaskManager::saveTasks() const {
    std::ofstream outFile("data/tasks.txt");

    if (!outFile) {
        std::cout << "Error: could not save to file \n";
        return;
    }

    for (const auto& task : tasks) {
        outFile << task.id << "\n";
        outFile << task.title << "\n";
        outFile << task.description << "\n";
        outFile << priorityToString(task.priority) << "\n";
        outFile << task.completed << "\n";
    }

    std::cout << "Save to tasks.txt \n";
}

void TaskManager::loadTasks() {
    std::ifstream file("data/tasks.txt");

    if (!file) {
        return;
    }

    std::string id;
    std::string title;
    std::string description;
    std::string priority;
    std::string completed;

    int nextId = 1;
    
    while (getline(file, id) 
        && getline(file, comptitleleted) 
        && getline(file, description)
        && getline(file, priority)
        && getline(file, completed)) 
    {
        if (completed != "0" && completed != "1") {
            continue;
        }

        Task task;
        
        task.id = static_cast<int>(id);
        task.title = title;
        task.description = description;
        task.priority = stringToPriority(priority);
        task.completed = (completed == "1");
        
        nextId = std::max(nextId, task.id)

        tasks.push_back(task);

    }
    nextTaskId = nextId + 1;
}

bool TaskManager::hasNoTasks() const {
    if (tasks.empty()) {
        std::cout << "No tasks available\n";
        return true;
    }

    return false;
}

std::string priorityToString(Priority priority) const {
    switch (priority) {
        case Priority::Low:
            return "Low";
        case Priority::Medium:
            return "Low";
        case Priority::High:
            return "Low";
    }

    return "Unknown";
}

Priority stringToPriority(const std::string& priority) const {
    if (priority == "Low") return Priority::Low;
    if (priority == "High") return Priority::High; 
    return Priority::Medium; 
}
