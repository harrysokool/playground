#include <iostream>
#include <string>
#include <sys/socket.h>
#include <netinet/in.h>
#include <unistd.h>
#include <sstream>
#include <unordered_map>

struct Request {
    std::string method;
    std::string path;
    std::string version;
    std::unordered_map<std::string, std::string> headers;
    std::string body;
    bool valid = false;
};

struct Response {
    std::string body;
    std::string status;
};

Request readRequest(int clientSocket) {
    Request req;
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
            return req;
        }
        request.append(buffer, bytesReceived);
    }

    size_t headerEnd = request.find("\r\n\r\n");
    std::string headers = request.substr(0, headerEnd);
    std::string body = request.substr(headerEnd+4);

    size_t contentLength = 0;
    size_t pos = headers.find("Content-Length:");
    if (pos != std::string::npos) {
        size_t valueStart = pos + 15;

        contentLength = std::stoul(headers.substr(valueStart));
    }

    while (body.size() < contentLength) {
        int bytesReceived = recv(
            clientSocket,
            buffer, 
            sizeof(buffer),
            0
        );

        if (bytesReceived <= 0) {
            std::cout << "Disconnected\n";
            return req;
        }
        body.append(buffer, bytesReceived);
    }

    std::istringstream requestStream(request);
    std::istringstream headerStream(headers);
    std::string line;

    requestStream >> req.method >> req.path >> req.version;
    req.body = body;

    std::getline(headerStream, line);
    while (std::getline(headerStream, line)) {
        if (!line.empty() && line.back() == '\r') {
            line.pop_back();
        }

        size_t colonPos = line.find(":");
        if (colonPos == std::string::npos) {
            continue;
        }

        std::string key = line.substr(0, colonPos);
        std::string val = line.substr(colonPos+1);

        if (!val.empty() && val.front() == ' ') {
            val.erase(0, 1);
        }

        req.headers[key] = val;
    }

    req.valid = true;
    return req;
}

std::string buildResponse(const Response& res) {
    return "HTTP/1.1 " + res.status + "\r\n" +
        "Content-Type: text/plain\r\n"
        "Content-Length: " + std::to_string(res.body.size()) + "\r\n" +
        "Connection: close\r\n" +
        "\r\n" +
        res.body;
}

bool sendAll(int clientSocket, const std::string& data) {
    size_t totalSent = 0;

    while (totalSent < data.size()) {
        int bytesSent = send(
            clientSocket,
            data.c_str() + totalSent,
            data.size() - totalSent,
            0
        );

        if (bytesSent <= 0) {
            return false;
        }

        totalSent += bytesSent;
    }

    return true;

}


void handleClient(int clientSocket) {
    Request req = readRequest(clientSocket);
    if (!req.valid) {
        return;
    }

    // build response
    Response res;
    
    if (req.method == "GET" && req.path == "/") {
        res.status = "200 OK";
        res.body = "Hello from C++";
    } else if (req.method == "GET" && req.path == "/about") {
        res.status = "200 OK";
        res.body = "About page";
    } else if (req.method == "POST" && req.path == "/message") {
        res.status = "200 OK";
        res.body = "Received: " + req.body;
    } else {
        res.status = "404 Not Found";
        res.body = "route not found";
    }

    std::string response = buildResponse(res);

    if (!sendAll(clientSocket, response)) {
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

    int reuseAddr = 1;

    if (setsockopt(
        serverSocket,
        SOL_SOCKET,
        SO_REUSEADDR,
        &reuseAddr,
        sizeof(reuseAddr)
        ) == -1) {
            std::cerr << "Failed to set SO_REUSEADDR.\n";
            close(serverSocket);
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