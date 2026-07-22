#include "TaskManager.h"

#include <fstream>
#include <iostream>
#include <limits>
#include <string>


void TaskManager::run() {
    loadTasks(tasks);

    while (true){
        int choiceNo;

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

        // check input range
        if (choiceNo <= 0 || choiceNo > 7) {
            std::cout << "Not a valid option!";
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
            reopenTask(tasks);
        }
        if (choiceNo == 7) {
            break;
        }
    }

    saveTasks(tasks);
    std::cout << "Goodbye!" << std::endl;
}

void TaskManager::addTasks() {
    ;
}

void TaskManager::deleteTask() {
    ;
}

void TaskManager::editTask() {
    ;
}

void TaskManager::displayTasks() const {
    ;
}

void TaskManager::completeTask() {
    ;
}

void TaskManager::reopenTask() {
    ;
}

void TaskManager::saveTasks() const {
    ;
}

void TaskManager::loadTasks() {
    ;
}