#include <iostream>
 
#include <sys/socket.h>
#include <netinet/in.h>
#include <unistd.h>

int main() {
    // AF_INET = IP4, SOCK_STREAM = TCP
    // "OS, create a TCP networking endpoint for me"
    int serverSocket = socket(AF_INET, SOCK_STREAM, 0);

    if (serverSocket < 0) {
        std::cerr << "Failed to create socket\n";
        return 1;
    }

    std::cout << "Socket created successfully\n";

    close(serverSocket);

    return 0;
}