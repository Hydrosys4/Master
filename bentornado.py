from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from start import app
import networkmod

http_server = HTTPServer(WSGIContainer(app))
http_server.listen(networkmod.PUBLICPORT)
IOLoop.instance().start()
