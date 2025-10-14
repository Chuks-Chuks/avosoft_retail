import random
from datetime import datetime, timedelta

class CarrierAPI:
    def __init__(self, carrier: str):
        self.carrier = carrier

    def create_shipment(self, order_data, shipping_address):
        tracking_number = f"1Z{random.randint(1000000000000000, 9999999999999999)}"
        return {
            "carrier": self.carrier,
            "tracking_number": tracking_number,
            "status": "label_created",
            "shipping_cost": round(random.uniform(8.99, 29.99), 2),
            "estimated_delivery": (datetime.now() + timedelta(days=random.randint(2, 5))).isoformat(),
            "label_url": f"https://mock-{self.carrier}.com/labels/{tracking_number}.pdf"
        }


class MockCourierService:
    def __init__(self):
        self.carriers = {
            'UPS': MockUPSAPI(),
            'FedEx': MockFedExAPI(),
        }
    
    def create_shipment(self, order, destination):
        carrier = self.select_carrier(destination)
        return self.carriers[carrier].create_shipment(order, destination)
    
    def select_carrier(self, destination):
        # Business logic for carrier selection
        if destination.get('state') in ['CA', 'NV', 'AZ']:
            return 'UPS'
        elif destination.get('country', 'USA') != 'USA':
            return 'FedEx'  # FedEx for international in mock
        else:
            return random.choice(['UPS', 'FedEx'])
