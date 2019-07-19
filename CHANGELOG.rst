1.6.1 (2019-07-19)
------------------

* cachelib import fix

1.6 (2019-07-19)
----------------

* use cachelib instead of werkzeug

1.5 (2019-06-26)
----------------

* multiple authentication methods (you can use `-a` argument multiple times)

1.4 (2019-03-11)
----------------

* foris-ws: nicer optional imports loading
* new authentication method (session in werkzeug's FileCache) implemented

1.3 (2019-01-31)
----------------

* mqtt: can set path to credentials file
* controller_id format update
* make ubus and mqtt buses optional

1.2 (2019-01-20)
----------------

* test updates - handle situation that mqtt advertizements are official notifications (remote.advertize)
* notifications for webclients extended by controller_id

1.1 (2018-11-09)
----------------

* mqtt message bus support implemented

1.0 (2018-11-09)
----------------

* using more mature websockets framework (based on asyncio)

0.2 (2018-08-14)
----------------

* python3 compatibility

0.1.3 (2018-07-30)
------------------

* properly handle termination via sigterm signal

0.1.2 (2018-07-30)
------------------

* using entry_points for console scripts
* print version to debug console
* print version using --version argument

0.1.1 (2017-10-23)
------------------

* ubus authentication fix
* small CI update (to test branches properly)

0.1 (2017-10-20)
----------------

* initial version published
* websocket server part based on websocket_server.WebsocketServer
* interchangeable bus using foris-client (ubus or unix-socket)
* authentication via ubus or none
* ipv4 + ipv6 support
* tests
