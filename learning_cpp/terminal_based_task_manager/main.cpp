#include <iostream>
#include <limits>
#include <string>
#include <vector>

void addTasks(std::vector<std::string>& tasks, const std::string& name);

void displayTasks(const std::vector<std::string>& tasks);

int main() {
    std::string name;
    std::vector<std::string> tasks;

    std::cout << "What is your name? ";
    std::getline(std::cin, name);

    addTasks(tasks, name);
    displayTasks(tasks);

    return 0;
}

void addTasks(std::vector<std::string>& tasks, const std::string& name) {
    int taskCount = 0;

    std::cout << "Hello " << name
              << ". How many tasks do you want to complete today? ";

    std::cin >> taskCount;

    if (taskCount < 1 || taskCount > 10)
    {
        std::cout << "Please enter a number between 1 and 10.\n";
        return;
    }

    std::cin.ignore(
        std::numeric_limits<std::streamsize>::max(),
        '\n'
    );

    for (int i = 1; i <= taskCount; ++i)
    {
        std::string task;

        std::cout << "Task " << i << ": ";
        std::getline(std::cin, task);

        tasks.push_back(task);
    }
}

void displayTasks(const std::vector<std::string>& tasks) {
    if (tasks.empty())
    {
        std::cout << "No tasks were added.\n";
        return;
    }

    std::cout << "\nThese are your tasks:\n";

    for (std::size_t i = 0; i < tasks.size(); ++i)
    {
        std::cout << "Task " << i + 1
                  << ": " << tasks[i] << '\n';
    }
}