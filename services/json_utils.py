try:
    import orjson
    ORJSON_AVAILABLE = True
except ImportError:
    import json
    ORJSON_AVAILABLE = False

def loads(data):
    if ORJSON_AVAILABLE:
        return orjson.loads(data)
    else:
        if isinstance(data, bytes):
            data = data.decode("utf-8")
        return json.loads(data)

def dumps(data, indent=None):
    if ORJSON_AVAILABLE:
        options = 0
        if indent:
            options |= orjson.OPT_INDENT_2
        return orjson.dumps(data, option=options)
    else:
        return json.dumps(data, indent=indent).encode("utf-8")

def get_read_mode():
    return 'rb'

def get_write_mode():
    return 'wb'
