from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from start import application
import networkmod

http_server = HTTPServer(WSGIContainer(application))
http_server.listen(networkmod.LOCALPORT)
IOLoop.instance().start()
