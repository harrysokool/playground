#include <iostream>
#include <string>
#include <sys/socket.h>
#include <netinet/in.h>
#include <unistd.h>

int main() {
    int serverSocket = socket(AF_INET, SOCK_STREAM, 0);
    if (serverSocket == -1) {
        std::cerr << "Socket creation failed\n";
        return 1;
    }

    sockaddr_in serverAddr{};
    serverAddr.sin_family = AF_INET;
    serverAddr.sin_port = htons(8080);
    serverAddr.sin_addr.s_addr = INADDR_ANY;

    int bindRes = bind(
        serverSocket,
        reinterpret_cast<sockaddr*>(&serverAddr),
        sizeof(serverAddr)
    );

    if (bindRes == -1) {
        std::cerr << "Bind failed.\n";
        close(serverSocket);
        return 1;
    }

    int listenRes = listen(
        serverSocket,
        5
    );

    if (listenRes == -1) {
        std::cerr << "Listen failed.\n";
        close(serverSocket);
        return 1;
    }

    std::cout << "Waiting for a client...\n";

    int clientSocket = accept(serverSocket, nullptr, nullptr);
    if (clientSocket == -1) {
        std::cerr << "Accept failed.\n";
        close(serverSocket);
        return 1;
    }

    std::cout << "Client connected\n";

    char buffer[1024];
    int bytesReceived = recv(
        clientSocket,
        buffer,
        sizeof(buffer)-1,
        0
    );

    if (bytesReceived <= 0) {
        std::cout << "Disconnected\n";
        close(serverSocket);
        close(clientSocket);
        return 1;
    }

    buffer[bytesReceived] = '\0';

    std::cout << "\nClient: " << buffer << '\n';

    // trying to extract the method and route
    std::string request(buffer);
    if (request.find("GET /about ") == 0) {
        std::cout << "about route requested\n";
    }


    std::string response =
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: text/plain\r\n"
        "Content-Length: 14\r\n"
        "\r\n"
        "Hello from C++";

    int bytesSent = send(
        clientSocket,
        response.c_str(),
        response.size(),
        0
    );

    if (bytesSent == -1) {
        std::cout << "Send failed\n";
    }

    close(serverSocket);
    close(clientSocket);

    return 0;
}