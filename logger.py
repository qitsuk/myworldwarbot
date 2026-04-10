_emit_fn = None

def set_emit(fn):
    global _emit_fn
    _emit_fn = fn

def log(message):
    if _emit_fn:
        _emit_fn(message)
    print(message)
