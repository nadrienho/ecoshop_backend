from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings

# --- USER PROFILES ---
class Profile(models.Model):
    ROLE_CHOICES = [
        ("customer", "Customer"),
        ("vendor", "Vendor"),
        ("shop_admin", "Shop Admin"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="customer")
    shop_name = models.CharField(max_length=255, null=True, blank=True)
    bio = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.role}"

# --- PRODUCT CATALOG ---
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, help_text="URL-friendly name")

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

class Product(models.Model):
    MATERIAL_CHOICES = [
        ("recycled_polyester", "Recycled Polyester"),
        ("virgin_polyester", "Virgin Polyester"),
        ("cotton", "Cotton"),
    ]

    TRANSPORT_MODE_CHOICES = [
        ("air", "Air"),
        ("truck", "Truck"),
        ("sea", "Sea"),
    ]

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    vendor = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    # New fields for EcoScore calculation
    carbon_footprint = models.FloatField(default=0.0)  # Score for Carbon Footprint (1-100)
    material_sustainability = models.FloatField(default=0.0)  # Score for Material Sustainability (1-100)
    longevity = models.FloatField(default=0.0)  # Score for Longevity (1-100)
    certifications = models.FloatField(default=0.0)  # Score for Certifications (1-100)

    # Fields for CO2 calculation
    weight = models.FloatField(default=0.0)  # Weight in kilograms
    material_type = models.CharField(max_length=50, choices=MATERIAL_CHOICES, default="cotton")
    transport_distance = models.FloatField(default=2.0)  # Distance in kilometers
    transport_mode = models.CharField(max_length=10, choices=TRANSPORT_MODE_CHOICES, default="truck")
    energy_usage = models.FloatField(default=0.0)  # Energy usage in kWh
    grid_intensity = models.FloatField(default=0.2)  # Default grid intensity (kg CO2 per kWh)

    # CO2 fields
    co2_baseline = models.FloatField(default=0.0)  # Baseline CO2 emissions
    actual_co2 = models.FloatField(default=0.0)  # Actual CO2 emissions
    co2_saved = models.FloatField(default=0.0)  # CO2 saved

    def calculate_co2_baseline(self):
        """
        Calculate the baseline CO2 emissions based on the product category.
        """
        baseline_lookup = {
            "Recycled": 7.0,
            "Houseware": 25.0,
            "Clothings": 10.0,
        }
        return baseline_lookup.get(self.category.name, 0.0)
    
    def calculate_actual_co2(self):
        """
        Calculate the actual CO2 emissions for the product.
        """
        # Materials Impact
        material_emission_factors = {
            # Textiles & Fabrics
            "recycled_polyester": 3.0,
            "virgin_polyester": 12.0,
            "organic_cotton": 2.5,
            "conventional_cotton": 5.0,
            "linen": 1.5,           # Very eco-friendly
            "hemp": 1.2,            # Carbon sequestering
            "wool": 14.0,           # High due to methane from sheep
            "nylon": 16.0,          # Energy intensive synthetic
            "silk": 25.0,           # High processing footprint

            # Packaging & Plastics
            "recycled_cardboard": 0.5,
            "virgin_paper": 1.2,
            "recycled_plastic_pet": 1.5,
            "virgin_plastic_pet": 3.5,
            "bioplastic_pla": 2.0,
            "glass": 1.2,           # Heavy to transport, but recyclable
            "aluminum_recycled": 0.6,
            "aluminum_virgin": 11.5, # Massive energy saving via recycling

            # Electronics & Metals
            "steel": 1.9,
            "copper": 3.8,
            "lithium_ion_battery": 15.0, # Per kg of battery
            
            # Building / Hard Goods
            "bamboo": 0.5,          # Rapidly renewable
            "cork": 0.2,            # Carbon negative in some studies
            "hardwood_timber": 0.8,
            "concrete": 0.15,       # Low per kg, but used in massive quantities
        }
        material_impact = self.weight * material_emission_factors.get(self.material_type, 0.0)

        # Transport Impact
        transport_emission_factors = {
            "air": 0.50,  # kg CO2 per tonne-km
            "truck": 0.10,  # kg CO2 per tonne-km
            "sea": 0.01,  # kg CO2 per tonne-km
        }
        transport_impact = (self.weight / 1000) * self.transport_distance * transport_emission_factors.get(self.transport_mode, 0.0)

        # Energy Impact
        energy_impact = self.energy_usage * self.grid_intensity

        # Total CO2 Actual
        return material_impact + transport_impact + energy_impact
    
    def calculate_co2_saved(self):
        """
        Calculate CO2 saved as the difference between baseline and actual CO2 emissions.
        """
        return max(self.co2_baseline - self.actual_co2, 0.0)
    
    def save(self, *args, **kwargs):
        """
        Override the save method to calculate and store baseline_co2, actual_co2, and co2_saved.
        """
        self.co2_baseline = self.calculate_co2_baseline()
        self.actual_co2 = self.calculate_actual_co2()
        self.co2_saved = self.calculate_co2_saved()
        super().save(*args, **kwargs)

    @property
    def eco_score(self):
        """
        Calculate the EcoScore using the weighted formula:
        Score = (C × 0.40) + (M × 0.30) + (L × 0.20) + (Cert × 0.10)
        """
        C = self.carbon_footprint
        M = self.material_sustainability
        L = self.longevity
        Cert = self.certifications

        # Weighted average formula
        return round((C * 0.40) + (M * 0.30) + (L * 0.20) + (Cert * 0.10), 2)

    def __str__(self):
        return self.name




    # @property
    # def co2_baseline(self):
    #     """
    #     Lookup table for baseline CO2 emissions based on product category.
    #     """
    #     baseline_lookup = {
    #         "Recycled": 7.0,
    #         "Houseware": 25.0,
    #         "Clothings": 0.1,
    #     }
    #     return baseline_lookup.get(self.category.name, 0.0)
    
    # @property
    # def co2_actual(self):
    #     """
    #     Calculate the actual CO2 emissions for the product.
    #     """
    #     # Materials Impact
    #     material_emission_factors = {
    #         # Textiles & Fabrics
    #         "recycled_polyester": 3.0,
    #         "virgin_polyester": 12.0,
    #         "organic_cotton": 2.5,
    #         "conventional_cotton": 5.0,
    #         "linen": 1.5,           # Very eco-friendly
    #         "hemp": 1.2,            # Carbon sequestering
    #         "wool": 14.0,           # High due to methane from sheep
    #         "nylon": 16.0,          # Energy intensive synthetic
    #         "silk": 25.0,           # High processing footprint

    #         # Packaging & Plastics
    #         "recycled_cardboard": 0.5,
    #         "virgin_paper": 1.2,
    #         "recycled_plastic_pet": 1.5,
    #         "virgin_plastic_pet": 3.5,
    #         "bioplastic_pla": 2.0,
    #         "glass": 1.2,           # Heavy to transport, but recyclable
    #         "aluminum_recycled": 0.6,
    #         "aluminum_virgin": 11.5, # Massive energy saving via recycling

    #         # Electronics & Metals
    #         "steel": 1.9,
    #         "copper": 3.8,
    #         "lithium_ion_battery": 15.0, # Per kg of battery
            
    #         # Building / Hard Goods
    #         "bamboo": 0.5,          # Rapidly renewable
    #         "cork": 0.2,            # Carbon negative in some studies
    #         "hardwood_timber": 0.8,
    #         "concrete": 0.15,       # Low per kg, but used in massive quantities
    #     }
    #     material_impact = self.weight * material_emission_factors.get(self.material_type, 0.0)

    #     # Transport Impact
    #     transport_emission_factors = {
    #         "air": 0.50,  # kg CO2 per tonne-km
    #         "truck": 0.10,  # kg CO2 per tonne-km
    #         "sea": 0.01,  # kg CO2 per tonne-km
    #     }
    #     transport_impact = (self.weight / 1000) * self.transport_distance * transport_emission_factors.get(self.transport_mode, 0.0)

    #     # Energy Impact
    #     energy_impact = self.energy_usage * self.grid_intensity

    #     # Total CO2 Actual
    #     return material_impact + transport_impact + energy_impact



    # @property
    # def eco_score(self):
    #     """
    #     Calculate the EcoScore using the weighted formula:
    #     Score = (C × 0.40) + (M × 0.30) + (L × 0.20) + (Cert × 0.10)
    #     """
    #     C = self.carbon_footprint
    #     M = self.material_sustainability
    #     L = self.longevity
    #     Cert = self.certifications

    #     # Weighted average formula
    #     return round((C * 0.40) + (M * 0.30) + (L * 0.20) + (Cert * 0.10), 2)
    
    # @property
    # def co2_saved(self):
    #     """
    #     Calculate CO2 saved as the difference between baseline and actual CO2 emissions.
    #     """
    #     return max(self.co2_baseline - self.co2_actual, 0.0)

    # def __str__(self):
    #     return self.name
    
class SavedProduct(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="saved_products")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="saved_by")
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "product")  # Prevent duplicate saves

# --- ORDERS & SUSTAINABILITY TRACKING ---
class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=255)
    street = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    region = models.CharField(max_length=100)
    post_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)
    delivery_option = models.CharField(max_length=50, choices=[("standard", "Standard"), ("express", "Express")])
    total_cost = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')    
    # This field is key for your Eco-Shop metrics!
    total_carbon_impact = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    @property
    def total_price(self):
        # This calculates the total on the fly based on related order items
        return sum(item.product.price * item.quantity for item in self.items.all())

    def __str__(self):
        return f"Order {self.id} by {self.user.username}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2) # Price at the time of purchase

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="cart")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cart of {self.user.username}"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} x {self.product.name} in {self.cart.user.username}'s cart"


