#include "TaskManager.h"

#include <fstream>
#include <iostream>
#include <limits>
#include <string>


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
        std::cout << "Task title: ";
        std::getline(std::cin, task.title);

        std::cout << "Task Description: ";
        std::getline(std::cin, task.description);

        tasks.push_back(task);
    }
}

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
        std::cout << i + 1 << ". "
          << (tasks[i].completed ? "[x] " : "[ ] ")
          << tasks[i].title
          << "\n"
          << tasks[i].description
          << '\n';
    }
}

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
        outFile << task.title << "\n";
        outFile << task.completed << "\n";
        outFile << task.description << "\n";
    }

    std::cout << "Save to tasks.txt \n";
}

void TaskManager::loadTasks() {
    std::ifstream file("data/tasks.txt");

    if (!file) {
        return;
    }

    std::string title;
    std::string completed;
    std::string description;
    
    while (getline(file, title) && getline(file, completed) && getline(file, description)) {
        if (completed != "0" && completed != "1") {
            continue;
        }

        Task task;
        task.title = title;
        task.description = description;
        task.completed = (completed == "1");
        tasks.push_back(task);
    }
}

bool TaskManager::hasNoTasks() const {
    if (tasks.empty()) {
        std::cout << "No tasks available\n";
        return true;
    }

    return false;
}

