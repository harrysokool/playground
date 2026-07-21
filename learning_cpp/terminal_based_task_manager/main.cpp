#include <iostream>
#include <limits>
#include <string>
#include <vector>
#include <fstream>

struct Task {
    std::string title;
    std::string description = "";
    bool completed = false;
};

void startTaskManager();

void addTasks(std::vector<Task>& tasks);

void deleteTask(std::vector<Task>& tasks);

void displayTasks(const std::vector<Task>& tasks);

void completeTask(std::vector<Task>& tasks);

void editTask(std::vector<Task>& tasks);

void loadTasks(std::vector<Task>& tasks);

void saveTasks(const std::vector<Task>& tasks);


int main() {
    startTaskManager();
    return 0;
}

void startTaskManager() {
    std::vector<Task> tasks;
    loadTasks(tasks);

    while (true){
        int choiceNo;

        std::cout << "\n===== Task Manager =====\n" 
            << "1. Add tasks \n"
            << "2. Display tasks \n"
            << "3. Delete task \n"
            << "4. Complete a task \n"
            << "5. Edit task\n"
            << "6. Exit \n"
            << "Enter your choice: ";

        if (!(std::cin >> choiceNo)) {
            std::cout << "Please enter a number.\n";

            // this is to clear the error state
            std::cin.clear();
            // this is to clear the input from the user previously entered
            std::cin.ignore(
                std::numeric_limits<std::streamsize>::max(),
                '\n'
            );
            continue;
        }

        // need to check input from user
        if (choiceNo <= 0 || choiceNo > 6) {
            std::cout << "GET OUT!" << std::endl;
            continue;
        }
        
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
            completeTask(tasks);
        }
        if (choiceNo == 5) {
            editTask(tasks);
        }
        if (choiceNo == 6) {
            break;
        }
    }

    saveTasks(tasks);
    std::cout << "Goodbye!" << std::endl;
}

void addTasks(std::vector<Task>& tasks) {
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

        std::cout << "Task " << i << ": ";
        std::getline(std::cin, task.title);

        tasks.push_back(task);
    }
}

void deleteTask(std::vector<Task>& tasks) {
    if (tasks.empty()) {
        std::cout << "No tasks available! \n";
        return;
    }

    std::cout << "Tasks: \n";

    for (std::size_t i = 0; i < tasks.size(); i++) {
        std::cout << i + 1 << ". " << tasks[i].title << "\n";
    }

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

void completeTask(std::vector<Task>& tasks) {
    if (tasks.empty()) {
        std::cout << "Nothing to complete";
        return;
    }

    // list out all the tasks
    displayTasks(tasks);

    // ask user which task is compeleted
    int idx;
    std::cout << "Enter task number to be mark completed: ";

    // check the input
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

    // mark the task as completed
    tasks[idx-1].completed = true;

    // display all tasks
    displayTasks(tasks);
}

void displayTasks(const std::vector<Task>& tasks) {
    if (tasks.empty()) {
        std::cout << "No tasks were added.\n";
        return;
    }

    std::cout << "\nThese are your tasks:\n";

    for (std::size_t i = 0; i < tasks.size(); ++i) {
        std::cout << i + 1 << ". "
          << (tasks[i].completed ? "[x] " : "[ ] ")
          << tasks[i].title
          << '\n';
    }
}

void editTask(std::vector<Task>& tasks) {
    if (tasks.empty()) {
        std::cout << "Nothing to edit";
        return;
    }

    // list out all the tasks
    displayTasks(tasks);

    // ask user which task to edit
    int idx;
    std::cout << "Enter task number to edit: ";

    // check the input
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

    // now let the user to edit the title of the task
    std::string newTitle;
    std::cout << "Enter new task title: ";

    if (!(std::cin >> newTitle)) {
        std::cout << "Please enter a valid title.\n";

        std::cin.clear();
        std::cin.ignore(
            std::numeric_limits<std::streamsize>::max(),
            '\n'
        );
        return;
    }

    tasks[idx-1].title = newTitle;

    // display all tasks
    displayTasks(tasks);
}

void loadTasks(std::vector<Task>& tasks) {
    std::ifstream file("tasks.txt");
    // check if file exist
    if (!file) {
        return;
    }

    std::string title;
    std::string completed;
    
    while (getline(file, title) && getline(file, completed)) {
        if (completed != "0" && completed != "1") {
            continue;
        }

        Task task;
        task.title = title;
        task.completed = (completed == "1");
        tasks.push_back(task);
    }
}

void saveTasks(const std::vector<Task>& tasks) {
    std::ofstream outFile("tasks.txt");

    if (!outFile) {
        std::cout << "Error: could not save to file \n";
        return;
    }

    for (const auto& task : tasks) {
        outFile << task.title << "\n";
        outFile << task.completed << "\n";
    }

    std::cout << "Save to tasks.txt \n";
}