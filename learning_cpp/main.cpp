#include <iostream>
#include <vector>

using namespace std;

void addTasks(vector<string>& tasks,const string& name);
void display_tasks(const vector<string>& tasks);

int main() {
    string name;
    vector<string> tasks;

    cout << "What is your name: ";
    cin >> name;
    addTasks(tasks, name);
    display_tasks(tasks);

    return 0;
}


void addTasks(vector<string>& tasks,const string& name) {
    int task_count = 0;
    cout << "Hello " << name 
        << " How many tasks do you want to complete today?";
    cin >> task_count;

    if (task_count <= 0 || task_count >= 11) {
        cout << "GET OUT!";
    } else {
        for (int i = 1; i <= task_count; i++) {
            string task;
            cout << "Task " << i << ": ";
            cin >> task;
            tasks.push_back(task);
        }
    }
}

void display_tasks(const vector<string>& tasks) {
    if (tasks.empty()) {
        cout << "GET OUT";
    } else {
        cout << "These are your tasks: \n";
        for (int i = 0; i < tasks.size(); i++) {
            cout << "Task " << i+1 << ": " << tasks[i] << "\n";
        }
    }
}

