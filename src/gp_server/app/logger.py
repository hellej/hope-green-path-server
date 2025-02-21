import time
from datetime import datetime


class Logger:
    """A somewhat generic logger class that can be used to write log messages to gunicorn,
    log file and/or console/terminal output.

    Attributes:
        app_logger (optional): A logger object of a Flask/Gunicorn application.
        b_printing (optional): A boolean variable indicating whether logs should be printed
            to standard console/terminal output.
        log_file (optional): A name for a log file (in the root of the application) where
            log messages will be written.
    """

    def __init__(
        self,
        app_logger=None,
        b_printing: bool = False,
        log_file: str = None,
        level: str = 'info'
    ):
        self.app_logger = app_logger
        self.b_printing = b_printing
        self.log_file = log_file
        self.level = {'debug': 4, 'info': 3, 'warning': 2, 'error': 1}[level]

    def print_log(self, text, level):
        """Prints a log message to console/terminal and/or to a log file (if specified at init).
        The log message is prefixed with current time and the given logging level.
        """
        log_prefix = datetime.utcnow().strftime('%y/%m/%d %H:%M:%S') + f' [{level}] '
        if self.b_printing:
            print(log_prefix + text)
        if self.log_file:
            with open(self.log_file, 'a') as the_file:
                the_file.write(log_prefix + text + '\n')

    def debug(self, text: str):
        if self.level >= 4:
            self.print_log(text, 'DEBUG')
        if self.app_logger:
            self.app_logger.debug(text)

    def info(self, text: str):
        if self.level >= 3:
            self.print_log(text, 'INFO')
        if self.app_logger:
            self.app_logger.info(text)

    def warning(self, text: str):
        if self.level >= 2:
            self.print_log(text, 'WARNING')
        if self.app_logger:
            self.app_logger.warning(text)

    def error(self, text: str):
        self.print_log(text, 'ERROR')
        if self.app_logger:
            self.app_logger.error(text)

    def critical(self, text: str):
        self.print_log(text, 'CRITICAL')
        if self.app_logger:
            self.app_logger.critical(text)

    def duration(
        self,
        time1,
        text,
        round_n: int = 3,
        unit: str = 's',
        log_level: str = 'debug'
    ) -> None:
        log_str = ''
        if unit == 's':
            time_elapsed = round(time.time() - time1, round_n)
            log_str = '--- %s s --- %s' % (time_elapsed, text)
        elif unit == 'ms':
            time_elapsed = round((time.time() - time1) * 1000)
            log_str = '--- %s ms --- %s' % (time_elapsed, text)

        if self.app_logger:
            if log_level == 'debug':
                self.debug(log_str)
            elif log_level == 'info':
                self.info(log_str)
