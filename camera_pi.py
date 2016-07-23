import time
import io
import threading

try:
	__import__("cv2")
except ImportError:
	ISRPI=False
else:
	import cv2
	ISRPI=True


class Camera(object):
	thread = None  # background thread that reads frames from camera
	frame = None  # current frame is stored here by background thread
	last_access = 0  # time of last client access to the camera

	def initialize(self):
		if Camera.thread is None:
			# start background frame thread
			Camera.thread = threading.Thread(target=self._thread)
			Camera.thread.start()

			# wait until frames start to be available
			while self.frame is None:
				time.sleep(0)

	def get_frame(self):
		Camera.last_access = time.time()
		self.initialize()
		return self.frame

	@classmethod
	def _thread(cls):
			camera_port = 0
			camera=cv2.VideoCapture(camera_port)
			# camera setup
			camera.set(5,20) #frame rate
			camera.set(3,640)
			camera.set(4,360)
			# max resolution 1280x720


			# let camera warm up
			time.sleep(2)
			while True:
					rc,img = camera.read()
					retval,buf=cv2.imencode(".jpg",img,(cv2.IMWRITE_JPEG_QUALITY,75))
					cls.frame=buf.tostring()


					# if there hasn't been any clients asking for frames in
					# the last 10 seconds stop the thread
					if time.time() - cls.last_access > 10:
							#del(camera)
							camera.release()
							break

			cls.thread = None
