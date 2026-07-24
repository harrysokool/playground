#include "TaskManager.h"

#include <algorithm>
#include <cctype>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>

void TaskManager::run() {
    loadTasks();

    while (true) {
        int choiceNo;

        if (!readInteger(
                "\n===== Task Manager =====\n"
                "1. Add tasks\n"
                "2. Display tasks\n"
                "3. Delete task\n"
                "4. Complete a task\n"
                "5. Edit task\n"
                "6. Reopen task\n"
                "7. Exit\n"
                "Enter your choice: ",
                choiceNo,
                1,
                7)) {
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
                std::cout << "Goodbye!\n";
                return;
        }
    }
}

void TaskManager::addTasks() {
    int taskCount;

    if (!readInteger(
            "How many tasks do you want to complete today? ",
            taskCount,
            1,
            10)) {
        return;
    }

    for (int i = 1; i <= taskCount; ++i) {
        Task task;

        std::cout << "Task " << i << ":\n";

        std::cout << "Task title: ";
        std::getline(std::cin, task.title);

        if (task.title.empty()) {
            std::cout << "Task title cannot be empty.\n";
            --i;
            continue;
        }

        std::cout << "Task description: ";
        std::getline(std::cin, task.description);

        int priorityChoice;

        if (!readInteger(
                "Priority:\n"
                "1. Low\n"
                "2. Medium\n"
                "3. High\n"
                "Enter priority: ",
                priorityChoice,
                1,
                3)) {
            --i;
            continue;
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
        }

        task.id = nextTaskId++;
        tasks.push_back(task);
    }

    saveTasks();
}

void TaskManager::deleteTask() {
    if (hasNoTasks()) {
        return;
    }

    displayTasks();

    int id;
    if (!readInteger("Enter task ID to remove: ", id)) {
        return;
    }

    auto taskIter = std::find_if(
        tasks.begin(),
        tasks.end(),
        [id](const Task& task) {
            return task.id == id;
        }
    );

    if (taskIter == tasks.end()) {
        std::cout << "Task not found.\n";
        return;
    }

    tasks.erase(taskIter);
    saveTasks();

    std::cout << "Task removed successfully.\n";
    displayTasks();
}

void TaskManager::editTask() {
    if (hasNoTasks()) {
        return;
    }

    displayTasks();

    int id;
    if (!readInteger("Enter task ID to edit: ", id)) {
        return;
    }

    Task* task = findTaskById(id);

    if (task == nullptr) {
        std::cout << "Task not found.\n";
        return;
    }

    std::string newTitle;
    std::cout << "New title: ";
    std::getline(std::cin, newTitle);

    if (newTitle.empty()) {
        std::cout << "Task title cannot be empty.\n";
        return;
    }

    std::string newDescription;
    std::cout << "New description: ";
    std::getline(std::cin, newDescription);

    if (newDescription.empty()) {
        std::cout << "Task description cannot be empty.\n";
        return;
    }

    std::string newPriority;
    std::cout << "New priority (Low, Medium, High): ";
    std::getline(std::cin, newPriority);

    for (char& character : newPriority) {
        character = static_cast<char>(
            std::tolower(static_cast<unsigned char>(character))
        );
    }

    if (newPriority != "low" &&
        newPriority != "medium" &&
        newPriority != "high") {
        std::cout << "Invalid priority.\n";
        return;
    }

    task->title = newTitle;
    task->description = newDescription;
    task->priority = stringToPriority(newPriority);

    saveTasks();

    std::cout << "Task updated successfully.\n";
    displayTasks();
}

void TaskManager::displayTasks() const {
    if (hasNoTasks()) {
        return;
    }

    std::cout << "\nThese are your tasks:\n";

    for (const auto& task : tasks) {
        std::cout << "ID " << task.id << ": "
                  << (task.completed ? "[x] " : "[ ] ")
                  << task.title
                  << " | Priority: "
                  << priorityToString(task.priority)
                  << '\n'
                  << "   Description: "
                  << task.description
                  << '\n';
    }
}

void TaskManager::completeTask() {
    if (hasNoTasks()) {
        return;
    }

    displayTasks();

    int id;
    if (!readInteger("Enter task ID to mark as completed: ", id)) {
        return;
    }

    Task* task = findTaskById(id);

    if (task == nullptr) {
        std::cout << "Task not found.\n";
        return;
    }

    if (task->completed) {
        std::cout << "Task is already completed.\n";
        return;
    }

    task->completed = true;
    saveTasks();

    std::cout << "Task completed successfully.\n";
    displayTasks();
}

void TaskManager::reopenTask() {
    if (hasNoTasks()) {
        return;
    }

    displayTasks();

    int id;
    if (!readInteger("Enter task ID to reopen: ", id)) {
        return;
    }

    Task* task = findTaskById(id);

    if (task == nullptr) {
        std::cout << "Task not found.\n";
        return;
    }

    if (!task->completed) {
        std::cout << "Task is already incomplete.\n";
        return;
    }

    task->completed = false;
    saveTasks();

    std::cout << "Task reopened successfully.\n";
    displayTasks();
}

void TaskManager::saveTasks() const {
    std::ofstream outFile("data/tasks.txt");

    if (!outFile) {
        std::cout << "Error: could not save tasks.\n";
        return;
    }

    for (const auto& task : tasks) {
        outFile << task.id << '\n';
        outFile << task.title << '\n';
        outFile << task.description << '\n';
        outFile << priorityToString(task.priority) << '\n';
        outFile << task.completed << '\n';
    }
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
    int highestId = 0;

    while (std::getline(file, id) &&
           std::getline(file, title) &&
           std::getline(file, description) &&
           std::getline(file, priority) &&
           std::getline(file, completed)) {
        if (completed != "0" && completed != "1") {
            continue;
        }

        try {
            Task task;
            task.id = std::stoi(id);
            task.title = title;
            task.description = description;
            task.priority = stringToPriority(priority);
            task.completed = completed == "1";

            highestId = std::max(highestId, task.id);
            tasks.push_back(task);
        }
        catch (const std::invalid_argument&) {
            std::cout << "Warning: invalid task ID ignored.\n";
        }
        catch (const std::out_of_range&) {
            std::cout << "Warning: task ID is too large.\n";
        }
    }

    nextTaskId = highestId + 1;
}

bool TaskManager::hasNoTasks() const {
    if (tasks.empty()) {
        std::cout << "No tasks available.\n";
        return true;
    }

    return false;
}

std::string TaskManager::priorityToString(Priority priority) const {
    switch (priority) {
        case Priority::Low:
            return "Low";
        case Priority::Medium:
            return "Medium";
        case Priority::High:
            return "High";
    }

    return "Unknown";
}

Priority TaskManager::stringToPriority(const std::string& priority) const {
    if (priority == "Low" || priority == "low") {
        return Priority::Low;
    }

    if (priority == "High" || priority == "high") {
        return Priority::High;
    }

    return Priority::Medium;
}

Task* TaskManager::findTaskById(int id) {
    for (auto& task : tasks) {
        if (task.id == id) {
            return &task;
        }
    }

    return nullptr;
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
