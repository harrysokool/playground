#include <iostream>
#include <string>
#include <sys/socket.h>
#include <netinet/in.h>
#include <unistd.h>
#include <sstream>

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

    while (true) {
        char buffer[1024];

        // get request from client
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
    
        std::cout << "\nClient: " << buffer << '\n';
        
        // turn trying to extract the method and route
        std::string request(buffer);
        
        // build response
        std::string response;
        std::string body;
        std::string status;
        
        if (request.find("GET / ") == 0) {
            status = "200 OK";
            body = "Hello from C++";
        } else if (request.find("GET /about ") == 0) {
            status = "200 OK";
            body = "About page";
        } else {
            status = "404 Not Found";
            body = "route not found";
        }

        response =
            "HTTP/1.1 " + status + "\r\n" +
            "Content-Type: text/plain\r\n"
            "Content-Length: " + std::to_string(body.size()) + "\r\n"
            "\r\n" +
            body;
    
        int bytesSent = send(
            clientSocket,
            response.c_str(),
            response.size(),
            0
        );
    
        if (bytesSent == -1) {
            std::cout << "Send failed\n";
            break;
        }
    }

    close(serverSocket);
    close(clientSocket);

    return 0;
}