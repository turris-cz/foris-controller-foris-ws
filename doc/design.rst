Foris ws
========

Application listens on the top of foris communication bus for incoming notification a provide corresponding notification to connected websocket clients.


Goals
-----
* use foris-client to listen for incomming notifications (replacible bus - ubus, unix-socket, ...)
* websocket authentication - use multiple authentication backends (ubus, ...)
* reasonable thread management


Design
------

The application itself is multithreaded and consits of two listen threads and a shared client queue.

websocket listener
##################
* actually listens on an http ports for incomming connections
* performs authentication
* ThreadingMixin -> each request is handled in a new thread
* inserts a record into the client queue when a client connects + starts ping thread
* is responsible for the cleanup whenever a client disconnects
* performs an action whenever a msg is recieved


client queue
############
* contains a list of connected clients
* locks are required to handle the queue
* each client has a list of modules from which the notifications are read
* each client has a send function to send notification back to the connected client


notification listener
#####################
* uses foris-client library
* listens on multiple backends
* spawns a new thread whenever a notifications is recieved
* the thread iterates through the client queue and sends the notification to appropriate clients
