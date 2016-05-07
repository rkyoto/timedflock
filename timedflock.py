"""
timedflock
==========

`timedflock` module provides a file lock class `TimedFileLock` on Unix-like
platforms which uses `fcntl.flock` at its core and supports timeout.

`TimedFileLock` does not poll the file lock to support timeout. Instead, it
spawns a child process to do `fcntl.flock`. Because of this, the main process
does not actually hold the file lock. This means that `TimedFileLock` is not
re-entrant and behaves more like `threading.Lock`.

`TimedFileLock` supports both shared lock and exclusive lock. It can be used
as reader-writer lock.

Example
-------

```python
from timedflock import TimedFileLock

with TimedFileLock(lockfile, shared=False, timeout=5.5) as _lck:
    if _lck.locked():
        ...  # locked code here
    else:
        ...  # not locked
```

"""
from __future__ import print_function

import sys, os
import fcntl
import signal
import base64
import threading
import traceback
from subprocess import Popen, PIPE

try:
    import cPickle as pickle
except ImportError:
    import pickle

__all__ = ['TimedFileLock']

_PY_EXEC = sys.executable
_PY_FILE = os.path.realpath(__file__)

class TimedFileLock:
    """
    The file lock wrapper class. Use with Python's context manager.
    """

    def __init__(self, lockfile, shared=None, timeout=None):
        """
        Arguments:

        `lockfile`
            The path to the lock file. If the lock file does not exist, it
            will be created automatically.

        `shared`
            Acquire shared lock if True. Otherwise acquire exclusive lock.
            Exclusive lock is acquired by default.

        `timeout`
            Timeout value in fractional seconds. Set timeout=None or omit
            this argument to set infinite timeout. Set timeout=0 to set the
            operation non-blocking.

        """
        if timeout is not None:
            timeout = float(timeout)
            if timeout < 0:
                raise ValueError("Invalid timeout")

        self._config = {
            'lockfile': os.path.abspath(lockfile),
            'shared': bool(shared),
            'timeout': timeout,
        }
        self._subproc = None

    def __enter__(self):
        self._try_lock()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.locked():
            self._unlock()

    def _try_lock(self):
        proc = None
        try:
            config = base64.b64encode(pickle.dumps(self._config))
            proc = Popen([_PY_EXEC, '-u', _PY_FILE, config], stdin=PIPE, stdout=PIPE)

            outline = proc.stdout.readline()
            if outline != b'locked\n':
                # not locked
                proc.wait()
                proc = None

        except:
            if proc is not None and proc.poll() is None:
                proc.kill()
                proc = None

        self._subproc = proc
        return None

    def _unlock(self):
        if self._subproc.poll() is None:
            self._subproc.send_signal(signal.SIGINT)
            self._subproc.wait()

        self._subproc = None
        return None

    def locked(self):
        """Returns True if the file is locked."""
        return self._subproc is not None

def _watcher():
    sys.stdin.read()
    print('parent process exited', file=sys.stderr)
    os._exit(1)

def _handler(signum, frame):
    # signal handler
    print('received signal:', signum, file=sys.stderr)

if __name__ == '__main__':
    # set signal handler
    signal.signal(signal.SIGALRM, _handler)
    signal.signal(signal.SIGINT, _handler)

    # load config
    config = pickle.loads(base64.b64decode(sys.argv[1]))

    # watch stdin in case parent process exits
    watcher = threading.Thread(target=_watcher)
    watcher.daemon = True
    watcher.start()

    with open(config['lockfile'], 'ab') as _file:
        lock_fd = _file.fileno()
        lock_op = fcntl.LOCK_SH if config['shared'] else fcntl.LOCK_EX

        timeout = config['timeout']
        if timeout is not None:
            if timeout > 0:
                signal.setitimer(signal.ITIMER_REAL, timeout)
            else:
                lock_op |= fcntl.LOCK_NB  # non-blocking

        locked = True
        try:
            fcntl.flock(lock_fd, lock_op)
        except:
            locked = False

        try:
            # reset timer
            signal.setitimer(signal.ITIMER_REAL, 0)
            if locked:
                sys.stdout.write('locked\n')
                sys.stdout.flush()
                signal.pause()
        except:
            traceback.print_exc()

        if locked:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)  # unlock
