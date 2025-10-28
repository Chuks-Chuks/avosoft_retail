# carrier_api_server.py
import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from avosoft_engine.services.carrier_service import DatabaseCarrierService

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
svc = DatabaseCarrierService()


@app.route("/api/v1/carriers", methods=["GET"])
def list_carriers():
    try:
        country = request.args.get("country")
        if country:
            carriers = svc.get_carriers_for_country(country)
        else:
            carriers = svc.list_carriers()
        return jsonify({"success": True, "carriers": carriers})
    except Exception as e:
        app.logger.exception("list_carriers failed")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/v1/shipments", methods=["POST"])
def create_shipment():
    try:
        payload = request.get_json(force=True)
        order_id = payload.get("order_id")
        order_item_id = payload.get("order_item_id")
        destination = payload.get("destination") or {}
        origin_dc = payload.get("origin_dc_id")
        service_level = payload.get("service_level")

        if not order_id or not order_item_id:
            return jsonify({"success": False, "error": "order_id and order_item_id required"}), 400

        shipment = svc.create_shipment(order_id, order_item_id, destination, origin_dc, service_level)
        return jsonify({"success": True, "shipment": shipment})
    except Exception as e:
        app.logger.exception("create_shipment failed")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/v1/tracking/<tracking_number>", methods=["GET"])
def get_tracking(tracking_number):
    try:
        res = svc.get_tracking(tracking_number)
        if not res:
            return jsonify({"success": False, "error": "not found"}), 404
        return jsonify({"success": True, "tracking": res})
    except Exception as e:
        app.logger.exception("get_tracking failed")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/v1/webhooks/update", methods=["POST"])
def webhook_update():
    try:
        payload = request.get_json(force=True)
        svc.apply_webhook_update(payload)
        return jsonify({"success": True})
    except Exception as e:
        app.logger.exception("webhook_update failed")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "time": datetime.utcnow().isoformat()})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
