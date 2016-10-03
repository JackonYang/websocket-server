# -*- coding:utf-8 -*-
import tornado.httpserver
import tornado.web
import tornado.websocket
import tornado.ioloop
import tornado.gen

import tornadoredis

from tornado.options import define, options
define("port", default=8888, help="run on the given port", type=int)
define("db", default=2, help="Redis selected_db", type=int)

c = tornadoredis.Client()

default_channel = 1


class MainHandler(tornado.web.RequestHandler):
    def get(self, channel):
        channel = channel or default_channel
        self.render("index.html", channel=channel)


class NewMessageHandler(tornado.web.RequestHandler):
    def post(self, channel):
        message = self.get_argument('message')
        c.publish(channel, message)
        self.set_header('Content-Type', 'text/plain')
        self.write('sent: %s' % (message,))


class MessageHandler(tornado.websocket.WebSocketHandler):
    def check_origin(self, origin):
        return True

    def open(self, channel):
        self.channel = channel
        self.listen()

    @tornado.gen.engine
    def listen(self):
        self.client = tornadoredis.Client()
        self.client.connect()
        yield tornado.gen.Task(self.client.subscribe, self.channel)
        self.client.listen(self.on_message)

    def on_message(self, msg):
        if msg.kind == 'message':
            self.write_message(str(msg.body))
        if msg.kind == 'disconnect':
            # Do not try to reconnect, just send a message back
            # to the client and close the client connection
            self.write_message('The connection terminated '
                               'due to a Redis server error.')
            self.close()

    def on_close(self):
        if self.client.subscribed:
            self.client.unsubscribe(self.channel)
            self.client.disconnect()


application = tornado.web.Application(
    [
        (r'/(?P<channel>[0-9]+)?', MainHandler),
        (r'/(?P<channel>[0-9]+)/new', NewMessageHandler),
        (r'/websocket/(?P<channel>[0-9]+)', MessageHandler),
    ],
    debug=True
)

if __name__ == '__main__':
    tornado.options.parse_command_line()

    c.selected_db = options.db
    c.connect()

    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(options.port)
    print('Demo is runing at 0.0.0.0:%s\n'
          'Quit the demo with CONTROL-C' % options.port)
    tornado.ioloop.IOLoop.instance().start()
