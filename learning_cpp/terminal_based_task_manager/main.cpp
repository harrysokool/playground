#include <iostream>
#include <limits>
#include <string>
#include <vector>

void startTaskManager();

void addTasks(std::vector<std::string>& tasks);

void deleteTask(std::vector<std::string>& tasks);

void displayTasks(const std::vector<std::string>& tasks);


int main() {
    startTaskManager();
    return 0;
}

void startTaskManager() {
    std::vector<std::string> tasks;

    while (true){
        int choiceNo;

        std::cout << "===== Task Manager =====\n" 
            << "1. Add tasks\n"
            << "2. Display tasks\n"
            << "3. Delete task\n"
            << "4. Exit\n"
            << "Enter your choice: ";

        if (!(std::cin >> choiceNo)) {
            std::cout << "Please enter a number.\n";

            std::cin.clear();
            std::cin.ignore(
                std::numeric_limits<std::streamsize>::max(),
                '\n'
            );

            continue;
        }

        // need to check input from user
        if (choiceNo <= 0 || choiceNo > 4) {
            std::cout << "GET OUT!" << std::endl;
            continue;
        }
        
        // add tasks
        if (choiceNo == 1) {
            addTasks(tasks);
        } 
        if (choiceNo == 2) {
            displayTasks(tasks);
        }
        if (choiceNo == 3)  {
            deleteTask(tasks);
        } 
        if (choiceNo == 4) {
            break;
        }
    }

    std::cout << "GET OUT!" << std::endl;
}

void addTasks(std::vector<std::string>& tasks) {
    int taskCount = 0;

    std::cout << "Hello there. How many tasks do you want to complete today? ";
    if (!(std::cin >> taskCount)) {
        std::cout << "Please enter a number.\n";

        std::cin.clear();
        std::cin.ignore(
            std::numeric_limits<std::streamsize>::max(),
            '\n'
        );

        return;
    }

    if (taskCount < 1 || taskCount > 10) {
        std::cout << "Please enter a number between 1 and 10.\n";
        return;
    }

    std::cin.ignore(
        std::numeric_limits<std::streamsize>::max(),
        '\n'
    );

    for (int i = 1; i <= taskCount; ++i) {
        std::string task;

        std::cout << "Task " << i << ": ";
        std::getline(std::cin, task);

        tasks.push_back(task);
    }
}

void deleteTask(std::vector<std::string>& tasks) {
    if (tasks.empty()) {
        std::cout << "No tasks available! \n";
        return;
    }
    std::cout << "Tasks: \n";
    for (size_t i = 0; i < tasks.size(); i++) std::cout << i + 1 << ". " << tasks[i] << "\n";

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
        std::cout << "GET OUT";
        return;
    }

    tasks.erase(tasks.begin() + idx-1);
    std::cout << "Task removed. \n";

    displayTasks(tasks);
}


void displayTasks(const std::vector<std::string>& tasks) {
    if (tasks.empty()) {
        std::cout << "No tasks were added.\n";
        return;
    }

    std::cout << "\nThese are your tasks:\n";

    for (std::size_t i = 0; i < tasks.size(); ++i) {
        std::cout << "Task " << i + 1
                  << ": " << tasks[i] << '\n';
    }
}