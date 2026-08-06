#include <iostream>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <string>


int main() {
    // this is the "phone" we will use to dial in
    int clientSocket = socket(AF_INET, SOCK_STREAM, 0);

    // locate the addr we want to dial in
    sockaddr_in serverAddr{};
    serverAddr.sin_family = AF_INET;
    serverAddr.sin_port = htons(8080);
    inet_pton(
        AF_INET,
        "127.0.0.1",
        &serverAddr.sin_addr
    );
    
    // now dial into that address
    int connectRes = connect(
        clientSocket,
        reinterpret_cast<sockaddr*>(&serverAddr),
        sizeof(serverAddr)
    );

    if (connectRes == -1) {
        std::cerr << "Connect failed.\n";
        return 1;
    }

    std::cout << "Connected to server\n";

    std::string msg = "Hello from the other side.";

    int bytesSent = send(
        clientSocket,
        msg.c_str(),
        msg.size(),
        0
    );

    if (bytesSent == -1) {
        std::cerr << "Send failed\n";
        return 1;
    }

    return 0;
}