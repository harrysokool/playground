#include <iostream>
#include <string>
#include <sys/socket.h>
#include <netinet/in.h>
#include <unistd.h>

int main() {
    // create the socket here, this is the endpoint, imagine this is a phone
    // create a tcp socket.
    // AF_INET = ip4
    // SOCK_STREAM = tcp
    int serverSocket = socket(AF_INET, SOCK_STREAM, 0);

    if (serverSocket == -1) {
        std::cerr << "Socket creation failed\n";
        return 1;
    }

    // serverAddress stores the server's network address.
    sockaddr_in serverAddr{};
    // tell the socket is ip4
    serverAddr.sin_family = AF_INET;
    // set the port
    serverAddr.sin_port = htons(8080);
    // set the ip
    // INADDR_ANY = Accept connections sent to any IP address on this computer.
    serverAddr.sin_addr.s_addr = INADDR_ANY;

    // Attach this socket to this IP address and port.
    int bindRes = bind(
        serverSocket,
        reinterpret_cast<sockaddr*>(&serverAddr),
        sizeof(serverAddr)
    );

    if (bindRes == -1) {
        std::cerr << "Bind failed.\n";
        return 1;
    }
    
    // 5 = at most 5 backlog
    int listenRes = listen(serverSocket, 5);

    if (listenRes == -1) {
        std::cerr << "Listen failed.\n";
        return 1;
    }

    
    std::cout << "Waiting for a client...\n";
    
    // accept() waits for a client to connect.
    int clientSocket = accept(serverSocket, nullptr, nullptr);
    if (clientSocket == -1) {
        std::cerr << "Accept failed.\n";
        return 1;
    }
    
    std::cout << "Client connected\n";
    
    while (true) {
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
            close(serverSocket);
            return 1;
        }

        if (bytesReceived == 0) {
            std::cout << "Client disconnected\n";
            close(clientSocket);
            close(serverSocket);
            return 0;
        }

        buffer[bytesReceived] = '\0';

        std::cout << "Client: " << buffer << '\n';

        std::string msg;
        std::cout << "Server: ";
        std::getline(std::cin, msg);

        int bytesSent = send(
            clientSocket,
            msg.c_str(),
            msg.size(),
            0
        );

        if (bytesSent == -1) {
            std::cerr << "Send failed\n";
            close(clientSocket);
            close(serverSocket);
            return 1;
        }

        // std::cout << "Server: " << buffer << '\n';
    }
    
    close(clientSocket);
    close(serverSocket);

    return 0;
}