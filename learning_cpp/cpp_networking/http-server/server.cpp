#include <iostream>
#include <string>
#include <sys/socket.h>
#include <netinet/in.h>
#include <unistd.h>
#include <sstream>
#include <unordered_map>
#include <thread>
#include <queue>
#include <mutex>
#include <condition_variable>
#include <vector>


constexpr size_t MAX_HEADER_SIZE = 8192;
constexpr size_t MAX_BODY_SIZE = 1024*1024;
constexpr size_t MAX_QUEUE_SIZE = 100;

std::queue<int> clientQueue;
std::mutex queueMutex;
std::condition_variable queueCondition;


struct Request {
    std::string method;
    std::string path;
    std::string version;
    std::unordered_map<std::string, std::string> headers;
    std::string body;
    bool valid = false;
    std::string error;
};

struct Response {
    std::string body;
    std::string status;
};


bool receiveHeaders(int clientSocket, Request& req, std::string& request) {
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
            return false;
        }

        request.append(buffer, bytesReceived);
        
        size_t headerEnd = request.find("\r\n\r\n");

        if (headerEnd == std::string::npos) {
            if (request.size() > MAX_HEADER_SIZE) {
                req.error = "Request headers too large";
                return false;
            }
        } else if (request.size() > MAX_HEADER_SIZE) {
            req.error = "Request headers too large";
            return false;
        }
    }

    return true;
}


bool parseContentLength(const std::string& headers, Request& req, size_t& contentLength) {
    size_t pos = headers.find("Content-Length:");
    if (pos != std::string::npos) {
        size_t valueStart = pos + 15;
        try {
            contentLength = std::stoul(headers.substr(valueStart));
            if (contentLength > MAX_BODY_SIZE) {
                req.error = "Request body too large";
                return false;
            }
        } catch (const std::exception&) {
            req.error = "Invalid Content-Length";
            return false;
        }
    }

    return true;
}


bool receiveBody(int clientSocket, std::string& body,const size_t contentLength) {
    char buffer[1024];
    while (body.size() < contentLength) {
        int bytesReceived = recv(
            clientSocket,
            buffer, 
            sizeof(buffer),
            0
        );

        if (bytesReceived <= 0) {
            std::cout << "Disconnected\n";
            return false;
        }

        body.append(buffer, bytesReceived);        
    }

    return true;
}


Request readRequest(int clientSocket) {
    Request req;
    std::string request;

    // get the request first
    if (!receiveHeaders(clientSocket, req, request)) {
        return req;
    }

    // parse the request
    size_t headerEnd = request.find("\r\n\r\n");
    std::string headers = request.substr(0, headerEnd);
    std::string body = request.substr(headerEnd+4);

    // get the content length
    size_t contentLength = 0;
    if (!parseContentLength(headers, req, contentLength)) {
        return req;
    }

    // now get the actual content
    if (!receiveBody(clientSocket, body, contentLength)) {
        return req;
    }

    std::istringstream requestStream(request);
    std::istringstream headerStream(headers);
    std::string line;

    if (!(requestStream >> req.method >> req.path >> req.version)) {
        req.error = "Malformed request line";
        return req;
    }
    if (req.version != "HTTP/1.1" && req.version != "HTTP/1.0") {
        req.error = "Unsupported HTTP version";
        return req;
    }
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
    Response res;

    if (!req.valid) {
        res.status = "400 Bad Request";
        res.body = req.error.empty()
            ? "Invalid HTTP request"
            : req.error;

        sendAll(clientSocket, buildResponse(res));
        return;
    }

    // build response
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


void workerLoop() {
    while (true) {
        int clientSocket;

        {
            std::unique_lock<std::mutex> lock(queueMutex);

            queueCondition.wait(lock, [] {
                return !clientQueue.empty();
            });

            clientSocket = clientQueue.front();
            clientQueue.pop();
        }

        handleClient(clientSocket);
        close(clientSocket);
    }    
}


int main() {
    int serverSocket = socket(AF_INET, SOCK_STREAM, 0);

    if (serverSocket == -1) {
        std::cerr << "Socket creation failed\n";
        return 1;
    }

    int reuseAddr = 1;
    // Allow this socket to bind to the address and port even if an earlier connection using them is still being cleaned up.
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

    constexpr int WORKER_COUNT = 4;
    std::vector<std::thread> workers;

    for (int i = 0; i < WORKER_COUNT; i++) {
        workers.emplace_back(workerLoop);
    }

    std::cout << "Waiting for a client...\n";
    
    while (true) {
        int clientSocket = accept(serverSocket, nullptr, nullptr);
        if (clientSocket == -1) {
            std::cerr << "Accept failed.\n";
            continue;
        }
        std::cout << "Client connected\n";
        bool queued = false;

        {
            std::lock_guard<std::mutex> lock(queueMutex);
            if (clientQueue.size() < MAX_QUEUE_SIZE) {
                clientQueue.push(clientSocket);
                queued = true;
            }
        }
        if (queued) {
            queueCondition.notify_one();
        } else {
            std::cerr << "Client queue is full\n";
            close(clientSocket);
        }
    }

    close(serverSocket);

    return 0;
}