    #!/bin/bash

    ### BEGIN INIT INFO
    # Provides:          mjpg_streamer
    # Required-Start:    $network
    # Required-Stop:     $network
    # Default-Start:     2 3 4 5
    # Default-Stop:      0 1 6
    # Short-Description: mjpg_streamer for webcam
    # Description:       Stream a video device over http.  http://<ip>:<port>/?action=stream
    ### END INIT INFO

    PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin";
    DAEMON="/usr/bin/mjpg_streamer";
    NAME="mjpg_streamer";
    DESC="MJPEG Streamer";

    VIDEO_DEV="/dev/video0";
    RESOLUTION="640x480";
    FRAME_RATE="20";
    JPEG_QUALITY="75";
    PORT="8080";
    WEB_DIR="/var/www/mjpg_streamer";
    PID_FILE="/var/run/${NAME}.pid";

    TXT_RESET=$(tput sgr0);
    TXT_RED=$(tput setaf 1);
    TXT_GREEN=$(tput setaf 2);
    TXT_YELLOW=$(tput setaf 3);
    TXT_BLUE=$(tput setaf 4);
    TXT_PURPLE=$(tput setaf 5);
    TXT_CYAN=$(tput setaf 6);
    TXT_WHITE=$(tput setaf 7);
    TXT_BOLD=$(tput bold);

    # Include defaults if available
    if [ -f /etc/default/mjpg_streamer ];
    then
            . /etc/default/mjpg_streamer;
    fi

    test -x ${DAEMON} || exit 0;

    . /lib/lsb/init-functions;

    function check_process {
            if [ -f /var/run/mjpg_streamer.pid ];
            then
                    PID=`cat ${PID_FILE}`;
            else
                    echo -n "${PID_FILE} does not exist";
            fi

            if [ "$( ps -p ${PID} -o comm= )" == "mjpg_streamer" ];
            then
                    return 0;
            else
                    return 1;
            fi
    }

    function start_mjpeg_daemon {
            echo -n "Starting ${DESC}";

            start-stop-daemon --quiet --background --pidfile ${PID_FILE} --make-pidfile --exec ${DAEMON} --start -- -i "/usr/lib/input_uvc.so -d ${VIDEO_DEV} -n -r ${RESOLUTION} -f ${FRAME_RATE} -q ${JPEG_QUALITY}" -o "/usr/lib/output_http.so -p ${PORT} -w ${WEB_DIR}" || true;

            sleep 1;

            # If check_process returns 0, process started successfully
            if check_process;
            then
                    echo -e "\t\t[${TXT_GREEN}Done${TXT_RESET}]";
            else
                    echo -e "\t\t[${TXT_RED}Failed${TXT_RESET}]";
            fi
    }

    function stop_mjpeg_daemon {
            echo -n "Stopping ${DESC}";
            start-stop-daemon --stop --quiet --pidfile ${PID_FILE} || true;

            sleep 1;

            # If check_process returns 1, process stopped successfully
            if check_process;
            then
                    echo -e "\t\t[${TXT_RED}Failed${TXT_RESET}]";
                    exit 1;
            else
                    echo -e "\t\t[${TXT_GREEN}Done${TXT_RESET}]";
            fi
    }

    case "${1}" in
            start)
                    start_mjpeg_daemon;
                    ;;
            stop)
                    stop_mjpeg_daemon;
                    ;;
            restart)
                    echo "Restarting ${DESC}: ";
                    stop_mjpeg_daemon;
                    sleep 1;
                    start_mjpeg_daemon;
                    ;;
            status)
                    status_of_proc -p ${PID_FILE} "${DAEMON}" mjpg_streamer && exit 0 || exit $?;
                    ;;
            *)
                    echo "Usage: ${NAME} {start|stop|restart|status}" >&2;
                    exit 1;
                    ;;
    esac;

    exit 0;

