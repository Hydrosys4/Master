from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from networkmod import LOCALPORT
from start import application


http_server = HTTPServer(WSGIContainer(application))

http_server.listen(LOCALPORT)

IOLoop.instance().start()

