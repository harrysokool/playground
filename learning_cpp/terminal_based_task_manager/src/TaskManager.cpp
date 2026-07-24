#include "TaskManager.h"

#include <fstream>
#include <iostream>
#include <limits>
#include <algorithm>
#include <stdexcept>
#include <string>
#include <cctype>


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

        std::cin.ignore(
            std::numeric_limits<std::streamsize>::max(),
            '\n'
        );
        
        task.id = nextTaskId;
        nextTaskId++;
        tasks.push_back(task);
    }

    saveTasks();
}

void TaskManager::deleteTask() {
    if (hasNoTasks()) return;

    displayTasks();

    int id;
    std::cout << "Enter Task ID to remove: ";

    if (!(std::cin >> id)) {
        std::cout << "Please enter a number.\n";

        std::cin.clear();
        std::cin.ignore(
            std::numeric_limits<std::streamsize>::max(),
            '\n'
        );
        return;
    }

    std::cin.ignore(
        std::numeric_limits<std::streamsize>::max(),
        '\n'
    );
    
    // remove the task by id, 
    // use iterator start to end, stop the iterator when id matches.
    auto taskIter = std::find_if(
        tasks.begin(),
        tasks.end(),
        const Task& task {
            return task.id == id;
        }
    );

    // if the iterator is at the end, which means not found
    if (taskIter == tasks.end()) {
        std::cout << "Task not found";
        return;
    }

    tasks.erase(taskIter);
    saveTasks();

    std::cout << "Task removed. \n";
    displayTasks();
}

void TaskManager::editTask() {
    if (hasNoTasks()) return;

    displayTasks();

    int id;
    std::cout << "Enter task ID to edit: ";

    if (!(std::cin >> id)) {
        std::cout << "Please enter a number.\n";

        std::cin.clear();
        std::cin.ignore(
            std::numeric_limits<std::streamsize>::max(),
            '\n'
        );
        return;
    }

    std::cin.ignore(
        std::numeric_limits<std::streamsize>::max(),
        '\n'
    );

    // now find the task in the vector list
    Task* task = findTaskById(id);
    if (task == nullptr) {
        std::cout << "Task not found";
        return;
    }

    // get new title
    std::cout << "New title: ";
    std::string newTitle;
    std::getline(std::cin, newTitle);
    if (newTitle.empty()) {
        std::cout << "Task title cannot be empty.\n";
        return;
    }
    
    // get new description
    std::cout << "New Description: ";
    std::string newDescription;
    std::getline(std::cin, newDescription);
    if (newDescription.empty()) {
        std::cout << "New task description is empty, so not updated.";
        return;
    }

    // get new priority
    std::cout << "New Priority (Low, Medium, High): ";
    std::string newPriority;    
    if (!(std::cin >> newPriority)) {
        std::cout << "Please enter valid priority.\n";

        std::cin.clear();
        std::cin.ignore(
            std::numeric_limits<std::streamsize>::max(),
            '\n'
        );
        return;
    }

    for (char &ch : newPriority) {
        ch = static_cast<char>(std::tolower(static_cast<unsigned char>(ch)));
    }
    
    if (newPriority!="low" && newPriority!="medium" && newPriority!="high") {
        std::cout << "Invalid priority.\n";
        return;
    }

    std::cin.ignore(
        std::numeric_limits<std::streamsize>::max(),
        '\n'
    );
    
    task->title = newTitle;
    task->description = newDescription;
    task->priority = stringToPriority(newPriority);

    std::cout << "Task updated successfully.\n";
    saveTasks();
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
                  << "\n"
                  << tasks[i].description
                  << "\n";
    }
}

void TaskManager::completeTask() {
    if (hasNoTasks()) return;

    displayTasks();

    int id;
    std::cout << "Enter task ID to be mark completed: ";

    if (!(std::cin >> id)) {
        std::cout << "Please enter a number.\n";

        std::cin.clear();
        std::cin.ignore(
            std::numeric_limits<std::streamsize>::max(),
            '\n'
        );
        return;
    }

    std::cin.ignore(
        std::numeric_limits<std::streamsize>::max(),
        '\n'
    );

    Task* task = findTaskById(id);
    if (task == nullptr) {
        std::cout << "Task not found";
        return;
    }

    task->completed = true;
    saveTasks();
    displayTasks();
}

void TaskManager::reopenTask() {
    if (hasNoTasks()) return;

    displayTasks();

    int id;
    std::cout << "Enter Task ID to reopen: ";

    if (!(std::cin >> id)) {
        std::cout << "Please enter a number.\n";

        std::cin.clear();
        std::cin.ignore(
            std::numeric_limits<std::streamsize>::max(),
            '\n'
        );
        return;
    }

    std::cin.ignore(
        std::numeric_limits<std::streamsize>::max(),
        '\n'
    );

    Task* task = findTaskById(id);
    if (task == nullptr) {
        std::cout << "Task not found";
        return;
    }

    if (!task->completed) {
        std::cout << "Task is incomplete, so cannot reopen";
        return;
    }

    task->completed = false;

    std::cout << "Task reopened successfully.\n";
    saveTasks();
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

    int highestId = 1;
    
    while (getline(file, id) 
        && getline(file, title) 
        && getline(file, description)
        && getline(file, priority)
        && getline(file, completed)) 
    {
        if (completed != "0" && completed != "1") {
            continue;
        }

        try {
            Task task;
            
            task.id = std::stoi(id);
            task.title = title;
            task.description = description;
            task.priority = stringToPriority(priority);
            task.completed = (completed == "1");
            
            highestId = std::max(highestId, task.id);
            tasks.push_back(task);
        } catch (const std::invalid_argument&) {
            std::cout << "Warning: invalid task ID ignored.\n";
        } catch (const std::out_of_range&) {
            std::cout << "Warning: task ID is too large.\n";
        }
    }
    nextTaskId = highestId + 1;
}

bool TaskManager::hasNoTasks() const {
    if (tasks.empty()) {
        std::cout << "No tasks available\n";
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
    for (auto& task: tasks) {
        if (task.id == id) {
            return &task;
        }
    }

    return nullptr;
}