# avosoft_retail/avosoft_engine/generators/users.py

import uuid, random
from .base import BaseGenerator, fake

GENDERS = ['male','female','non-binary','prefer not to say']
SOURCES = ['google','facebook','twitter','instagram','linkedin','email','direct','referral']
emails = ['gmail.com', 'yahoo.com', 'hotmail.com', 'example.com', 'outlook.com', 'icloud.com', 'daph.com']

class UsersGenerator(BaseGenerator):
    def generate_batch(self, n: int, ds: str):
        users = []
        for _ in range(n):
            gender = random.choice(GENDERS)
            nm = fake.name_male() if gender == 'male' else fake.name_female()
            first, last = nm.split()[0], nm.split()[-1]
            users.append({
                "id": str(uuid.uuid4()),
                "first_name": first,
                "last_name": last,
                "email": f"{first.lower()}.{last.lower()}{uuid.uuid4().hex}@{random.choice(emails)}",
                "age": fake.pyint(16, 80),
                "gender": gender,
                "state": fake.state(),
                "street_address": fake.street_address(),
                "postal_code": fake.postcode(),
                "city": fake.city(),
                "country": fake.country(),
                "latitude": float(fake.latitude()),
                "longitude": float(fake.longitude()),
                "traffic_source": random.choice(SOURCES),
                "created_at": f"{ds} 12:00:00",
                "dob": fake.date_of_birth(minimum_age=16, maximum_age=80).isoformat()
            })
        return users
