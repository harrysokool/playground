#include <iostream>
#include <string>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <thread>


void receiveMsg(int clientSocket) {
    while (true) {
        char buffer[1024];

        int bytesReceived = recv(
            clientSocket,
            buffer,
            sizeof(buffer)-1,
            0
        );
    
        if (bytesReceived <= 0) {
            std::cout << "Disconnected\n";
            break;
        }
    
        buffer[bytesReceived] = '\0';
    
        std::cout << "\nServer: " << buffer << '\n';
    }
}


int main() {
    // this is the "phone" we will use to dial in
    int clientSocket = socket(AF_INET, SOCK_STREAM, 0);

    if (clientSocket == -1) {
        std::cerr << "Socket creation failed\n";
        return 1;
    }

    // locate the addr we want to dial in
    sockaddr_in serverAddr{};
    serverAddr.sin_family = AF_INET;
    serverAddr.sin_port = htons(8080);
    if (inet_pton(
        AF_INET,
        "127.0.0.1",
        &serverAddr.sin_addr
    ) != 1) {
        std::cerr << "Invalid IP address\n";
        return 1;
    }
    
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

    std::thread receiver(receiveMsg, clientSocket);

    while (true){
        // now we send the msg
        std::string msg;
        std::cout << "Client: ";
        std::getline(std::cin, msg);

        if (msg == "quit") {
            break;
        }
        
        // msg.c_str() = Give send() the message as raw characters.
        int bytesSent = send(
            clientSocket,
            msg.c_str(),
            msg.size(),
            0
        );

        if (bytesSent == -1) {
            std::cerr << "Send failed\n";
            break;
        }

    }

    shutdown(clientSocket, SHUT_RDWR);

    receiver.join();

    close(clientSocket);

    return 0;
}