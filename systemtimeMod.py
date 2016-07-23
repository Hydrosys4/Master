import sys
import datetime

def _win_set_time(time_tuple):
    import pywin32
    # http://timgolden.me.uk/pywin32-docs/win32api__SetSystemTime_meth.html
    # pywin32.SetSystemTime(year, month , dayOfWeek , day , hour , minute , second , millseconds )
    dayOfWeek = datetime.datetime(time_tuple).isocalendar()[2]
    pywin32.SetSystemTime( time_tuple[:2] + (dayOfWeek,) + time_tuple[2:])


def _linux_set_time(time_tuple):
    import ctypes
    import ctypes.util
    import time

    # /usr/include/linux/time.h:
    #
    # define CLOCK_REALTIME                     0
    CLOCK_REALTIME = 0

    # /usr/include/time.h
    #
    # struct timespec
    #  {
    #    __time_t tv_sec;            /* Seconds.  */
    #    long int tv_nsec;           /* Nanoseconds.  */
    #  };
    class timespec(ctypes.Structure):
        _fields_ = [("tv_sec", ctypes.c_long),
                    ("tv_nsec", ctypes.c_long)]

    librt = ctypes.CDLL(ctypes.util.find_library("rt"))

    ts = timespec()
    ts.tv_sec = int( time.mktime( datetime.datetime( *time_tuple[:6]).timetuple() ) )
    ts.tv_nsec = time_tuple[6] * 1000000 # Millisecond to nanosecond

    # http://linux.die.net/man/3/clock_settime
    librt.clock_settime(CLOCK_REALTIME, ctypes.byref(ts))

def set_min_datetime():
	time_tuple = ( 2013, # Year
                  1, # Month
                  1, # Day
                  0, # Hour
                  0, # Minute
                  0, # Second
                  0, # Millisecond
              )

	# time tuple to datetime object
	mindate = datetime.datetime(*time_tuple[0:6])
	curdate= datetime.datetime.now()
	if curdate<mindate:
		if sys.platform=='linux2':
			_linux_set_time(time_tuple)

		elif  sys.platform=='win32':
			_win_set_time(time_tuple)

if __name__ == '__main__':
	

	set_min_datetime()
	
