from threading import Thread
from time import perf_counter, sleep

class ThreadManager:
    killed     = dict()
    exceptions = dict()
    result     = dict()
    pending    = []
    threadID   = 0

    def getThreadID():
        ThreadManager.threadID += 1
        return f'Thread-{ThreadManager.threadID - 1}'

    def run(function, *args, threadID=None, loopDelay=False, **kwargs):
        threadID = threadID or ThreadManager.getThreadID()
        ThreadManager.killed[threadID] = False
        def wrapper_loop(*args, **kwargs):
            while not ThreadManager.killed[threadID]:
                function(*args, **kwargs)
                sleep(loopDelay)
        func = function if loopDelay is False else wrapper_loop
        def wrapper_killed(*args, **kwargs):
            try:
                ThreadManager.result[threadID] = func(*args, **kwargs)                
            except Exception as e:
                ThreadManager.exceptions[threadID] = e
            finally:
                ThreadManager.killed[threadID] = True 
        Thread(target=wrapper_killed, args=args, kwargs=kwargs).start()
        return threadID

    def prepareRun(function, *args, threadID=None, loopDelay=False, **kwargs):
        assert 'job_ThreadManager_RunPending' in ThreadManager.killed, 'job_ThreadManager_RunPending not running'
        threadID = threadID or ThreadManager.getThreadID()
        ThreadManager.pending.append((function, args, threadID, loopDelay, kwargs))
        return threadID

    def isFinished(threadIDs):
        return all(ThreadManager.killed[threadID] for threadID in threadIDs)

    def kill(threadID):
        ThreadManager.killed[threadID] = True

    def killAll():
        ThreadManager.killed = {i: True for i in ThreadManager.killed}

#################### Timeout ####################
class Timeout(Exception):
    pass

def setTimeout(function, seconds, *args, pollInterval=0.1, **kwargs):
    threadID = ThreadManager.run(function, *args, **kwargs)
    start    = perf_counter()
    while True:
        if ThreadManager.killed[threadID]:
            return ThreadManager.result[threadID]
        elif perf_counter() >= start + seconds:
            raise Timeout
        sleep(pollInterval)

def SetTimeout(seconds, pollInterval=0.1):
    def wrapper(function):
        def wrapper1(*args, **kwargs):
            return setTimeout(function, seconds, *args, pollInterval=pollInterval, **kwargs)
        return wrapper1
    return wrapper

def job_ThreadManager_ClearKilledThreads():
    toClear = ThreadManager.killed.copy()
    for key in toClear:
        if toClear[key]:
            del ThreadManager.killed[key]
            
def job_ThreadManager_RunPending():            
    toRun = ThreadManager.pending  
    ThreadManager.pending = ThreadManager.pending[len(toRun):]
    for function, args, threadID, loopDelay, kwargs in toRun:
        ThreadManager.run(function, *args, threadID=threadID, loopDelay=loopDelay, **kwargs)

def startThreadManagerJobs():
    ThreadManager.run(job_ThreadManager_ClearKilledThreads, threadID='job_ThreadManager_ClearKilledThreads', loopDelay=10)
    ThreadManager.run(job_ThreadManager_RunPending, threadID='job_ThreadManager_RunPending', loopDelay=0)
