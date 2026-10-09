import json

import azure.functions as func


def main(req: func.HttpRequest) -> func.HttpResponse:
    """Sonda pública mínima para el balanceador y la evidencia funcional."""
    return func.HttpResponse(
        json.dumps({"status": "ok", "service": "tangamandapio-wms"}),
        status_code=200,
        mimetype="application/json",
    )
