#include <iostream>
#include <limits>
#include <string>
#include <vector>

void startTaskManager();

void addTasks(std::vector<std::string>& tasks);

void displayTasks(const std::vector<std::string>& tasks);


int main() {
    startTaskManager();
    return 0;
}

void startTaskManager() {
    std::vector<std::string> tasks;

    while (true){
        int choice_no;

        std::cout << "===== Task Manager =====\n" 
            << "1. Add tasks\n"
            << "2. Display tasks\n"
            << "3. Exit\n"
            << "Enter your choice: ";

        std::cin >> choice_no;

        // need to check input from user
        if (choice_no <= 0 || choice_no > 3) {
            std::cout << "GET OUT!" << std::endl;
            break;
        }
        
        // add tasks
        if (choice_no == 1) {
            addTasks(tasks);
        } else if (choice_no == 2) {
            displayTasks(tasks);
        } else if (choice_no == 3) {
            break;
        }
    }

    std::cout << "GET OUT!" << std::endl;
}

void addTasks(std::vector<std::string>& tasks) {
    int taskCount = 0;

    std::cout << "Hello there. How many tasks do you want to complete today? ";
    std::cin >> taskCount;

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