'''
Log information about all of the failures for a given run:

foreach map call:
DONE * start time, name, pset count, pset column names
DONE * worker exceptions with tracebacks and which pset caused them
* final .progress
* final .missing
* middle and final performance stats
* end

Another file to support checkpoint/restart

* for each .map() call:
* log initial psets
* record results in chunks as they come in
* on restart, rerun missing or provide previous results

'''
import datetime
import os
import sys
import socket


def atomic_create_ish(filenames):
    '''
    Figure out which on this list of filenames is unique.
    Not safe on NFS filesystems.
    '''
    for f in filenames:
        try:
            fd = open(f, 'xt')
        except FileExistsError:
            continue
        break
    else:
        raise ValueError('unable to open a unique logfile, rerun')

    return fd


logfd = None


def init(global_kwargs, pslogger_prefix='.paramsurvey-', pslogger_fd=None, **kwargs):
    # always log if pslogger_fd is set
    # otherwise, never log within pytest.
    if pslogger_fd is None and 'PYTEST_CURRENT_TEST' in os.environ:
        return

    middle = datetime.datetime.utcnow().strftime('%Y%m%d-%H%M%S')
    middleplus = datetime.datetime.utcnow().strftime('%Y%m%d-%H%M%S.%f')
    middles = (middle, middleplus, middleplus+'a')
    print('GREG, middles', repr(middles))
    print('GREG, pslogger_prefix', pslogger_prefix)
    filenames = [pslogger_prefix+m+'.log' for m in middles]
    print('GREG, filenames', filenames)

    global logfd
    if pslogger_fd:
        logfd = pslogger_fd
    else:
        logfd = atomic_create_ish([pslogger_prefix+m+'.log' for m in middles])

    print('paramsurvey starttime', middleplus, file=logfd)
    print('hostname', socket.gethostname())
    print('command line', repr(sys.argv), file=logfd)
    for e in sorted(['PYTHONPATH', 'VIRTUAL_ENV', 'CONDA_DEFAULT_ENV', 'CONDA_PREFIX']):
        if e in os.environ:
            print(e, os.environ[e], file=logfd)
    for p in sorted(['PARAMSURVEY', 'SINGULARITY']):
        s = repr([x for x in os.environ if x.startswith(p)])
        if s != '[]':
            print(p, 'env vars', s, file=logfd)
    print('python sys.version', ' '.join(sys.version.splitlines()), file=logfd)

    print('python modules:')
    for k in sorted(sys.modules):
        v = sys.modules[k]
        ver = getattr(v, '__version__', None)
        if ver is not None:
            print(' ', k, ver, file=logfd)

    logfd.flush()


def log(s):
    if logfd:
        print(s, file=logfd)


def finalize():
    logfd.close()