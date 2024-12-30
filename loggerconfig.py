LOG_SETTINGS = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'detailed': {
            'format': '%(asctime)s |  %(levelname)s | %(filename)s | %(funcName)s | %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'simple': {
            'format': '%(asctime)-2s %(name)28s - %(levelname)-10s %(message)s',
            'datefmt': '%H:%M:%S'
        },
    },
    'handlers': {
        'console':{
            'level':'DEBUG',
            'class':'logging.StreamHandler',
            'formatter': 'simple'
        },
        'access_file_handler':{
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'level': 'DEBUG',
            'formatter': 'simple',
            'filename': 'logfiles/hydrosystem.log',
            'backupCount': 3,
            'encoding': 'utf8',
            'when': 'midnight',
            'interval': 1,
            'delay': True
        },
        'actuator':{
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'DEBUG',
            'formatter': 'detailed',
            'filename': 'logfiles/actuator.log',
            'backupCount': 3,
            'encoding': 'utf8',
            'maxBytes': 1048576,
            'delay': True            
        },
        'exception_file_handler':{
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'level': 'ERROR',
            'formatter': 'detailed',
            'filename': 'logfiles/ex_hydrosystem.log',
            'backupCount': 3,
            'encoding': 'utf8',
            'when': 'midnight',
            'interval': 1,
            'delay': True
        }

    },
    'loggers': {
        'hydrosys4': {
            'handlers':['access_file_handler'],
            'propagate': False,
            'level':'DEBUG'
        },
        'actuator': {
            'handlers':['actuator'],
            'propagate': False,
            'level':'DEBUG'
        },
        'exception': {
            'handlers': ['exception_file_handler'],
            'level': 'ERROR',
            'propagate': False
        }
    }
}
