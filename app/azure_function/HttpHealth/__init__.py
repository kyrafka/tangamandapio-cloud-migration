import json


def main(req):
    """Health check deliberately independent of downstream Storage services."""
    return json.dumps({"status": "ok", "service": "tangamandapio-wms"})
