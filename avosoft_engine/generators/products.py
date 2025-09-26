# avosoft_retail/avosoft_engine/generators/products.py

import uuid, random, string
from .base import BaseGenerator, fake
import time

# ----- Department → Category → Subcategory (from your spec, expanded lightly) -----
DEPT_CATALOG = {
    "Electronics": {
        "Smartphones": ["Android Phones", "iPhones", "Refurbished"],
        "Laptops": ["Ultrabooks", "Gaming Laptops", "2-in-1"],
        "Headphones": ["Wireless", "Noise Cancelling", "In-Ear", "Over-Ear"],
        "Cameras": ["DSLR", "Mirrorless", "Action Cameras"],
        "TV & Home Theater": ["4K TV", "Projectors", "Soundbars", "OLED TV"]
    },
    "Home & Kitchen": {
        "Appliances": ["Microwaves", "Air Fryers", "Vacuum Cleaners", "Blenders"],
        "Cookware & Dining": ["Cookware Sets", "Knife Sets", "Dinnerware", "Bakeware"],
        "Furniture": ["Sofas", "Dining Tables", "Office Chairs", "Bookshelves"],
        "Bedding & Bath": ["Sheets", "Duvets", "Towels", "Pillows"]
    },
    "Clothing - Men": {
        "Tops": ["T-Shirts", "Shirts", "Polos", "Sweatshirts"],
        "Bottoms": ["Jeans", "Chinos", "Shorts", "Joggers"],
        "Outerwear": ["Jackets", "Coats", "Blazers", "Raincoats"],
        "Footwear": ["Sneakers", "Loafers", "Boots", "Sandals"]
    },
    "Clothing - Women": {
        "Tops": ["T-Shirts", "Blouses", "Sweaters", "Cardigans"],
        "Bottoms": ["Jeans", "Skirts", "Leggings", "Trousers"],
        "Dresses": ["Casual", "Formal", "Evening", "Summer"],
        "Footwear": ["Heels", "Flats", "Sneakers", "Boots"]
    },
    "Beauty & Personal Care": {
        "Skin Care": ["Moisturizers", "Serums", "Cleansers", "Sunscreen"],
        "Hair Care": ["Shampoo", "Conditioner", "Styling", "Hair Oil"],
        "Makeup": ["Foundation", "Mascara", "Lipstick", "Concealer"],
        "Fragrance": ["Eau de Parfum", "Eau de Toilette", "Body Mist"]
    },
    "Sports & Fitness": {
        "Training": ["Dumbbells", "Resistance Bands", "Yoga Mats"],
        "Cardio": ["Treadmills", "Bikes", "Rowers", "Ellipticals"],
        "Outdoor": ["Tents", "Backpacks", "Hiking Shoes", "Sleeping Bags"]
    },
    "Toys & Games": {
        "Building Sets": ["Blocks", "STEM Kits", "Magnetic Tiles"],
        "Action Figures": ["Superheroes", "Collectibles", "Anime"],
        "Board Games": ["Strategy", "Family", "Party"]
    },
    "Automotive": {
        "Car Electronics": ["Dash Cams", "Car Stereos", "OBD Scanners"],
        "Maintenance": ["Oil & Fluids", "Filters", "Wipers", "Brake Pads"],
        "Accessories": ["Seat Covers", "Floor Mats", "Phone Mounts", "Roof Racks"]
    },
    "Grocery": {
        "Beverages": ["Coffee", "Tea", "Juice", "Soda", "Energy Drinks"],
        "Snacks": ["Chips", "Nuts", "Chocolate", "Protein Bars"],
        "Pantry": ["Pasta", "Rice", "Sauces", "Spices"]
    },
    "Books": {
        "Fiction": ["Thrillers", "Romance", "Sci-Fi", "Fantasy"],
        "Non-Fiction": ["Biographies", "Business", "Self-Help", "History"],
        "Children": ["Picture Books", "Young Readers", "Early Learning"]
    },
    "Pet Supplies": {
        "Dog": ["Food", "Toys", "Collars", "Beds"],
        "Cat": ["Food", "Litter", "Toys", "Scratchers"],
        "Aquatic": ["Aquariums", "Filters", "Water Care", "Lights"]
    }
}

# ----- Brands (expanded) -----
BRANDS = {
    "Electronics": ["AcmeTech","Zenith","Voltix","Auralink","PixelPro","SkyWave","NovaSound","Kinetik","HyperVision"],
    "Home & Kitchen": ["Homely","ChefMate","CasaNova","NeatNest","PureHome","CookCraft","BrightHome","LuxeLiving"],
    "Clothing - Men": ["Northline","Forge & Co","UrbanTrail","VistaWear","Atlas & Row","StonePeak","Ridgeway"],
    "Clothing - Women": ["Luna & Ivy","HarborRose","Astra Moda","Willow & West","Sable & Sage","VelvetRow","Marina Lane"],
    "Beauty & Personal Care": ["GlowLab","PureEssence","NovaBeauty","SkinTheory","BloomCare","RadiantCo","Serenique"],
    "Sports & Fitness": ["IronPeak","RunCore","FlexLab","AeroFit","TrailForce","CoreMotion","LiftPro"],
    "Toys & Games": ["PlayWorks","FunFoundry","BrightBlocks","GiggleBox","StarForge Toys","KidzLab"],
    "Automotive": ["RoadMaster","DrivePro","AutoSage","TorqueX","GearGrid","MotoLine","StreetSense"],
    "Grocery": ["DailyHarvest","FreshFields","GoodGrain","Brew & Bean","FarmFresh","UrbanPantry","GreenLeaf"],
    "Books": ["RiverPress","OpenLeaf","Northbridge Publishing","Storyline Press","PageTurner","EpicReads","Quill & Oak"],
    "Pet Supplies": ["PawCo","WhiskerWorks","AquaDen","FurryFriends","PetHaven","CritterCare","PetPalace","HappyPaws","FurEver Friends","PetEssentials","PetJoy"]
}

# ----- SKU prefixes -----
SKU_PREFIX = {
    "Electronics": "ELE",
    "Home & Kitchen": "HMK",
    "Clothing - Men": "MEN",
    "Clothing - Women": "WMN",
    "Beauty & Personal Care": "BPC",
    "Sports & Fitness": "SPT",
    "Toys & Games": "TOY",
    "Automotive": "AUT",
    "Grocery": "GRC",
    "Books": "BOK",
    "Pet Supplies": "PET"
}

class ProductsGenerator(BaseGenerator):
    """Generates product catalog data."""
    def __init__(self):
        super().__init__()
        self.generated_skus = set()

    def _make_name(self, department: str, category: str, subcategory: str) -> str:
        # e.g., "Cobalt Wireless Headphones" / "Oak Dining Table"
        color_or_style = random.choice([fake.color_name(), fake.word().title()])
        base = f"{color_or_style} {subcategory}"
        return " ".join(w.capitalize() for w in base.split())

    def _sku(self, department: str) -> str:
        prefix = SKU_PREFIX.get(department, "GEN")
        nanos = time.time_ns()  # Nanosecond precision
        random_bits = random.getrandbits(32)  # Additional randomness
        return f"{prefix}-{nanos}{random_bits:08X}"  

    def generate_batch(self, n: int):
        rows = []
        depts = list(DEPT_CATALOG.keys())
        for _ in range(n):
            dept = random.choice(depts)
            category = random.choice(list(DEPT_CATALOG[dept].keys()))
            subcategory = random.choice(DEPT_CATALOG[dept][category])

            name = self._make_name(dept, category, subcategory)
            brand = random.choice(BRANDS[dept])
            cost = round(random.uniform(5, 180), 2)

            # margin logic by dept (grocery/books lower, electronics/fashion higher)
            margin = {
                "Grocery": (1.08, 1.35),
                "Books": (1.10, 1.50),
                "Electronics": (1.12, 1.90),
                "Clothing - Men": (1.25, 2.20),
                "Clothing - Women": (1.25, 2.20),
            }.get(dept, (1.12, 1.80))

            retail = round(cost * random.uniform(*margin), 2)
            sku = self._sku(dept)

            rows.append({
                "product_id": str(uuid.uuid4()),
                "cost": cost,
                "category": category,
                "name": name,
                "brand": brand,
                "retail_price": retail,
                "department": dept,
                "sku": sku,
                "subcategory": subcategory
            })
        return rows
