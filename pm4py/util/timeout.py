'''
    PM4Py â€“ A Process Mining Library for Python
Copyright (C) 2024 Process Intelligence Solutions UG (haftungsbeschrÃ¤nkt)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see this software project's root or
visit <https://www.gnu.org/licenses/>.

Website: https://processintelligence.solutions
Contact: info@processintelligence.solutions
'''
from threading import Thread
from typing import Any, Callable, Dict, Optional, Tuple
import ctypes


class FunctionTimedOut(TimeoutError):
    def __init__(
        self,
        timeout: float,
        func: Callable[..., Any],
        args: Optional[Tuple[Any, ...]] = None,
        kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.timeout = timeout
        self.func = func
        self.args = args if args is not None else ()
        self.kwargs = kwargs if kwargs is not None else {}
        func_name = getattr(func, "__name__", repr(func))
        super().__init__(f"Function '{func_name}' timed out after {timeout} seconds")


def _request_thread_stop(thread: Thread) -> None:
    ident = thread.ident
    if ident is None:
        return

    try:
        set_async_exc = ctypes.pythonapi.PyThreadState_SetAsyncExc
    except Exception:
        return

    set_async_exc.argtypes = [ctypes.c_ulong, ctypes.py_object]
    set_async_exc.restype = ctypes.c_int
    result = set_async_exc(ctypes.c_ulong(ident), ctypes.py_object(SystemExit))
    if result > 1:
        set_async_exc(ctypes.c_ulong(ident), None)


def func_timeout(
    timeout: float,
    func: Callable[..., Any],
    args: Optional[Tuple[Any, ...]] = None,
    kwargs: Optional[Dict[str, Any]] = None,
) -> Any:
    if timeout is None:
        return func(*(args or ()), **(kwargs or {}))
    if timeout <= 0:
        raise ValueError("timeout must be > 0")

    args = args if args is not None else ()
    kwargs = kwargs if kwargs is not None else {}

    result: Dict[str, Any] = {}
    error: Dict[str, BaseException] = {}

    def _runner() -> None:
        try:
            result["value"] = func(*args, **kwargs)
        except BaseException as exc:
            error["value"] = exc

    thread = Thread(target=_runner, daemon=True)
    thread.start()
    thread.join(timeout)

    if thread.is_alive():
        _request_thread_stop(thread)
        thread.join(0.05)
        raise FunctionTimedOut(timeout, func, args=args, kwargs=kwargs)

    if "value" in error:
        raise error["value"]

    return result.get("value")
