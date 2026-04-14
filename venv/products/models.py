from django.db import models

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, help_text="URL-friendly name")

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

class Product(models.Model):
    # Linking Product to Category (Many-to-One relationship)
    category = models.ForeignKey(
        Category, 
        related_name='products', 
        on_delete=models.SET_NULL, 
        null=True,
        blank=True
    )
    
    name = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Eco-Specific Fields
    material_composition = models.JSONField(
        help_text="e.g. {'organic_cotton': 80, 'recycled_poly': 20}"
    )
    carbon_footprint_kg = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        help_text="Total CO2e footprint for this product"
    )
    
    # Eco-Score (1-100)
    eco_score = models.IntegerField(default=0) 
    
    # Metadata
    image_url = models.URLField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name