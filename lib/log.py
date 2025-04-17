import io
import os
import time
import random
import inspect
import logging
import traceback
from functools import wraps, lru_cache

import numpy as np
import colorlog
from pydantic import BaseModel
from starlette.responses import Response

ENV = os.getenv("ENV", "TEST")


def unique_id():
    _id = f"{int(time.time() * 1000)}{int(random.random() * 1000000)}"
    return int(_id)


CLIENT = None
PRINT = False
IGNORE = "ignore"
_incr_id = unique_id()

PROJECT = "ChatTools"
_ENV_PROJECT = f"{PROJECT}_{ENV}"
LEVEL_INFO = logging.INFO
LEVEL_DEBUG = logging.DEBUG
LEVEL_ERROR = logging.ERROR

STATS = {}


@lru_cache()
def get_logger(logger_name=None, level=logging.INFO):
    logger = logging.getLogger(logger_name)

    # Set logger level
    logger.setLevel(level)

    # Create console handler
    stream_handler = logging.StreamHandler()
    color_formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(levelname)-8s%(reset)s %(blue)s%(message)s",
        datefmt=None,
        reset=True,
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red,bg_white",
        },
        secondary_log_colors={},
        style="%",
    )
    stream_handler.setFormatter(color_formatter)
    logger.addHandler(stream_handler)
    return logger


LOGGER = get_logger()


def uid():
    global _incr_id
    _incr_id += 1
    return _incr_id


def fn_name():
    return inspect.stack()[1][3]


def log_time(_id, message, s_time: float, function=""):
    if not function:
        frame = inspect.currentframe()
        if frame and frame.f_back and frame.f_back.f_code:
            function = frame.f_back.f_code.co_name

    message = get_use_time(time.time(), s_time) + f" {message}"

    return log(
        _id,
        message,
        function=function,
        use_time=round(time.time() - s_time, 4),
    )


def log(
    _id,
    message,
    _level=logging.INFO,
    function: str | None = None,
    use_time: float | None = None,
    len_limit=5000,
):
    if _id == IGNORE:
        return

    if not _id:
        _id = unique_id()

    if not function:
        frame = inspect.currentframe()
        if frame and frame.f_back and frame.f_back.f_code:
            function = frame.f_back.f_code.co_name

    function = f"\x1b[36;1m{function}\x1b[34m"

    _time = str(time.strftime("%Y-%m-%d %H:%M:%S"))
    message = f"{message}" if not isinstance(message, str) else message
    message = message if len(message) < len_limit else message[:len_limit] + "..."
    string = f"{_id} : {_time} : {function} : {message}"

    LOGGER.log(_level, string)

    if PRINT:
        if use_time:
            use_time = get_use_time(use_time, 0)
            print(f"{use_time} {string}")

        else:
            print(string)


def error(_id, message, function=None):
    return log(_id, f"{message}", _level=logging.ERROR, function=function)


def get_trace_back():
    fp = io.StringIO()
    traceback.print_exc(file=fp)
    return fp.getvalue()


def _process_arg(arg, _recur_time=5, _num=10):
    if _recur_time <= 0:
        return f"{arg}"[:200]

    if isinstance(arg, BaseModel):
        arg = arg.__dict__

    if isinstance(arg, Response):
        arg = arg.__dict__

    if isinstance(arg, dict):
        new_arg = {}
        for k, v in arg.items():
            if k == "vectors" and v is not None:
                new_arg[k] = len(v)
            else:
                new_arg[k] = _process_arg(v, _recur_time - 1)
        arg = new_arg

    elif isinstance(arg, list) or isinstance(arg, tuple):
        return [_process_arg(v, _recur_time - 1) for v in arg[:_num]]

    elif isinstance(arg, np.ndarray):
        arg = list(arg)
        return [_process_arg(v, _recur_time - 1) for v in arg[:_num]]

    return arg


def get_use_time(e_time: float, s_time: float):
    use_time = e_time - s_time
    if use_time <= 0.1:
        use_time = f"\x1b[32;1m{use_time:.4f}s\x1b[34m"
    elif use_time <= 0.5:
        use_time = f"\x1b[33;1m{use_time:.4f}s\x1b[34m"
    elif use_time <= 1:
        use_time = f"\x1b[34;1m{use_time:.4f}s\x1b[34m"
    elif use_time <= 5:
        use_time = f"\x1b[35;1m{use_time:.4f}s\x1b[34m"
    else:
        use_time = f"\x1b[31;1m{use_time:.4f}s\x1b[34m"
    return f"(use time: {use_time})"


def record(
    show_input: bool = True,
    show_return: bool = True,
    level: int = logging.INFO,
    show_args_ids=None,
    show_kwargs_ids=None,
    show_return_len: bool = False,
):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # generate a unique id for the log
            log_id = (
                uid()
                if "log_id" not in kwargs or not kwargs["log_id"]
                else kwargs["log_id"]
            )

            if log_id == IGNORE:
                kwargs["log_id"] = log_id
                return func(*args, **kwargs)

            if show_input:
                # record the parameters of the called function
                if show_args_ids and args:
                    log_args = [
                        _process_arg(args[arg_i])
                        for arg_i in show_args_ids
                        if len(args) > arg_i
                    ]
                else:
                    log_args = [_process_arg(arg) for arg in args]
                if show_kwargs_ids and kwargs:
                    log_kwargs = {
                        k: _process_arg(kwargs[k])
                        for k in show_kwargs_ids
                        if k in kwargs
                    }
                else:
                    log_kwargs = {k: _process_arg(v) for k, v in kwargs.items()}
                msg = f"args: {log_args}, kwargs: {log_kwargs}"
            else:
                msg = f"{len(args)} args, {len(kwargs)} kwargs"

            function = func.__name__
            log(
                log_id,
                msg,
                _level=level,
                function=f"[Inp] \x1b[33;1m{function}",
            )
            s_time = time.time()

            # exec the called function
            kwargs["log_id"] = log_id
            _ret = func(*args, **kwargs)

            e_time = time.time()
            msg = get_use_time(e_time, s_time)

            # modified the level of the msg according to the response
            _level = level
            if isinstance(_ret, dict):
                if "code" in _ret and "log_id" not in _ret:
                    _ret["log_id"] = log_id
                if "code" in _ret and _ret["code"] not in [1, 200]:
                    _level = logging.ERROR
                    if (not show_return or show_return_len) and "msg" in _ret:
                        msg += f" {_ret['msg']}"

            elif hasattr(_ret, "code"):
                if _ret.code not in [1, 200]:
                    _level = logging.ERROR
                    if (not show_return or show_return_len) and hasattr(_ret, "msg"):
                        msg += f" {_ret.msg}"

            if show_return:
                if show_return_len:
                    msg += f" return len: {len(_ret.data) if hasattr(_ret, 'data') else len(_ret)}"
                else:
                    msg += f" return {_process_arg(_ret)}"

            # record the response
            log(
                log_id,
                msg,
                _level=_level,
                function=f"[Out] \x1b[33;1m{function}",
            )
            return _ret

        return wrapper

    return decorator
