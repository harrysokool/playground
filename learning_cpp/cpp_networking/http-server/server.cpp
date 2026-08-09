#include <iostream>
#include <string>
#include <sys/socket.h>
#include <netinet/in.h>
#include <unistd.h>
#include <sstream>

struct Request {
    std::string method;
    std::string path;
    std::string version;
};

struct Response {
    std::string body;
    std::string status;
};


void handleClient(int clientSocket) {
    // get request from client
    std::string request;
    char buffer[1024];

    while (request.find("\r\n\r\n") == std::string::npos) {
        int bytesReceived = recv(
            clientSocket,
            buffer,
            sizeof(buffer),
            0
        );
        
        if (bytesReceived <= 0) {
            std::cout << "Disconnected\n";
            return;
        }

        request.append(buffer, bytesReceived);
    }

    std::cout << "\nRequest:\n" << buffer << '\n';

    // parse here
    // first get header
    size_t headerEnd = request.find("\r\n\r\n");
    std::string headers = request.substr(0, headerEnd);
    std::string body = request.substr(headerEnd+4);

    std::cout << "Headers:\n" << headers << '\n';
    std::cout << "Body: " << body << '\n';
    
    // turn trying to extract the method and route
    std::string request(buffer);
    std::istringstream requestStream(request);
    Request req;

    requestStream >> req.method >> req.path >> req.version;

    // build response
    Response res;
    
    if (req.method == "GET" && req.path == "/") {
        res.status = "200 OK";
        res.body = "Hello from C++";
    } else if (req.method == "GET" && req.path == "/about") {
        res.status = "200 OK";
        res.body = "About page";
    } else {
        res.status = "404 Not Found";
        res.body = "route not found";
    }

    std::string response =
        "HTTP/1.1 " + res.status + "\r\n" +
        "Content-Type: text/plain\r\n"
        "Content-Length: " + std::to_string(res.body.size()) + "\r\n"
        "\r\n" +
        res.body;

    int bytesSent = send(
        clientSocket,
        response.c_str(),
        response.size(),
        0
    );

    if (bytesSent == -1) {
        std::cout << "Send failed\n";
        return;
    }
}


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
    
    while (true) {
        // try to get more than 1 client
        int clientSocket = accept(serverSocket, nullptr, nullptr);
        if (clientSocket == -1) {
            std::cerr << "Accept failed.\n";
            continue;
        }
        std::cout << "Client connected\n";

        handleClient(clientSocket);

        close(clientSocket);
    }

    close(serverSocket);

    return 0;
}