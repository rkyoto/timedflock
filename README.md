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

Usage
-----

`TimedFileLock` should be used with Python's context manager.

Example:
```python
from timedflock import TimedFileLock

with TimedFileLock(lockfile, shared=False, timeout=5.5) as _lck:
    if _lck.locked():
        ...  # locked code here
    else:
        ...  # not locked
```

Python 2.7 and later 3.x versions should be supported. Tested on Ubuntu,
CentOS and some other Linux distros.

License
-------

Copyright 2016 Matt Jones <mattjones1811@hotmail.com>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
