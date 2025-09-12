# avosoft_retail/avosoft_engine/generators/distribution_centres.py

import uuid, random
from .base import BaseGenerator

class DistributionCentersGenerator(BaseGenerator):
    def generate_seed(self, n: int) -> list[dict]:
        centers = []
        for _ in range(n):
            centers.append({
                "id": str(uuid.uuid4()),
                "name": f"DC-{random.randint(100,999)}",
                "latitude": round(random.uniform(-60, 60), 6),
                "longitude": round(random.uniform(-150, 150), 6),
            })
        return centers
