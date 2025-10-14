import uuid
import random
from datetime import datetime, timedelta
from .base import BaseGenerator

class ShippingGenerator(BaseGenerator):
    def __init__(self):
        super().__init__()
        self.carriers = ['UPS', 'FedEx', 'USPS', 'DHL', 'OnTrac']
        
    def generate_shipments(self, order_items: list, user_addresses: dict):
        """Generate shipping records for shipped order items"""
        shipments = []
        
        for item in order_items:
            if item.get('shipped_at') and not item.get('delivered_at'):
                # Only create shipments for items that are shipped but not delivered
                shipment = self._create_shipment(item, user_addresses)
                shipments.append(shipment)
        
        return shipments

    def _create_shipment(self, order_item, user_addresses):
        """Create a single shipment record"""
        carrier = self._select_carrier(order_item)
        tracking_prefix = self._get_tracking_prefix(carrier)
        
        shipped_at = datetime.fromisoformat(order_item['shipped_at'].replace('Z', '+00:00'))
        
        return {
            'shipment_id': str(uuid.uuid4()),
            'order_id': order_item['order_id'],
            'order_item_id': order_item['id'],
            'carrier': carrier,
            'tracking_number': f'{tracking_prefix}{random.randint(1000000000000000, 9999999999999999)}',
            'status': 'in_transit',
            'created_at': order_item['created_at'],
            'shipped_at': order_item['shipped_at'],
            'estimated_delivery': self._estimate_delivery(shipped_at).isoformat(),
            'actual_delivery': None,  # Will be set via webhook
            'shipping_cost': round(random.uniform(5.99, 25.99), 2),
            'origin_address': self._generate_origin_address(),
            'destination_address': user_addresses.get(order_item['user_id'], {})
        }

    def _select_carrier(self, order_item):
        """Select carrier based on business rules"""
        # Simple rule: Use UPS for expedited, USPS for standard
        if random.random() < 0.3:  # 30% chance for expedited
            return 'UPS'
        else:
            return random.choice(['FedEx', 'USPS', 'DHL', 'OnTrac'])  # Added OnTrac to the carriers

    def _get_tracking_prefix(self, carrier):
        prefixes = {
            'UPS': '1Z', 
            'FedEx': 'FD', 
            'USPS': 'US', 
            'DHL': 'DH', 
            'OnTrac': 'OT'
        }
        return prefixes.get(carrier, 'TR')

    def _estimate_delivery(self, shipped_at):
        """Calculate estimated delivery date (2-7 days from shipment)"""
        return shipped_at + timedelta(days=random.randint(2, 7))

    # The warehouse already exist in the database as distribution centres. There would be no need to regenerate fresh warehouses. We can instead use the distribution centres.
    # I have removed the logic for the warehouse. 
