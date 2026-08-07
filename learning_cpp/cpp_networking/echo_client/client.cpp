#include <iostream>
#include <string>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>


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

    while (true){
        // now we send the msg
        std::string msg;
        std::cout << "Client: ";
        std::getline(std::cin, msg);

        // msg.c_str() = Give send() the message as raw characters.
        int bytesSent = send(
            clientSocket,
            msg.c_str(),
            msg.size(),
            0
        );

        if (bytesSent == -1) {
            std::cerr << "Send failed\n";
            close(clientSocket);
            return 1;
        }

        // now we try to recieve the msg
        char buffer[1024];
        int bytesReceived = recv(
            clientSocket,
            buffer,
            sizeof(buffer)-1,
            0
        );

        if (bytesReceived == -1) {
            std::cerr << "Receive failed\n";
            close(clientSocket);
            return 1;
        }

        if (bytesReceived == 0) {
            std::cout << "Server disconnected\n";
            close(clientSocket);
            return 0;
        }

        buffer[bytesReceived] = '\0';

        std::cout << "Server: " << buffer << '\n';
    }

    close(clientSocket);

    return 0;
}