from app import App
import threading

def _run(dev):
    _run.app = App(dev)
    _run.app.MainLoop()
    _run.app.Destroy()
    del _run.app

def test():
    _run.app.Invoke(_run.app.ShowTest)

def run(dev):
    if hasattr(_run, "app"):
        _run.app.Invoke(_run.app.ShowMain)
    else:
        t = threading.Thread(target = _run, args = (dev,))
        t.daemon = True
        t.start()