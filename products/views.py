from rest_framework import generics, viewsets, permissions, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from django.contrib.auth.models import User
from .models import Product, Profile, Category, Cart, CartItem, Order, OrderItem, SavedProduct
from .serializers import ProductSerializer, UserSerializer, UserMeSerializer, ProfileSerializer, CategorySerializer
from .permissions import IsVendorOrReadOnly
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from django.http import QueryDict
from django.db.models import Sum, F
from django.db.models.functions import TruncMonth


class ProductListView(ListAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = {
        'category': ['exact'],
        'price': ['lte', 'gte', 'exact'], # This enables price__lte and price__gte
    }
    ordering_fields = ['created_at', 'price']  # Enable sorting by created_at (newest) and price

    def get_queryset(self):
        print(self.request.GET)  # Log the query parameters
        return super().get_queryset()

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsVendorOrReadOnly]

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_saved_products(request):
    """
    Fetch all saved products for the authenticated user.
    """
    user = request.user
    print(f"Fetching saved products for user: {user}")
    saved_products = SavedProduct.objects.filter(user=user).select_related("product")
    print(f"Saved products: {saved_products}")
    data = [
        {
            "id": saved.product.id,
            "name": saved.product.name,
            "description": saved.product.description,
            "price": saved.product.price,
            #"vendor_name": saved.product.category.name,  # Assuming category is used as vendor
        }
        for saved in saved_products
    ]
    return Response(data, status=200)

@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def remove_saved_product(request, product_id):
    user = request.user
    try:
        saved_product = SavedProduct.objects.get(user=user, product_id=product_id)
        saved_product.delete()
        return Response({"message": "Product removed from saved."}, status=200)
    except SavedProduct.DoesNotExist:
        return Response({"error": "Product not found in saved list."}, status=404)

@api_view(["GET"])
def get_products(request):
    products = Product.objects.all()
    category = request.GET.get("category")
    price_lte = request.GET.get("price__lte")
    ordering = request.GET.get("ordering")

    if category:
        products = products.filter(category_id=category)
    if price_lte:
        products = products.filter(price__lte=price_lte)
    if ordering:
        products = products.order_by(ordering)

    serializer = ProductSerializer(products, many=True)
    return Response(serializer.data)


class UserDetailView(generics.RetrieveAPIView):
    """
    Get current authenticated user's profile with role information.
    Used for role-based redirects after login.
    """
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

class UserMeView(APIView):
    """
    Get the authenticated user's details
    GET /api/user/me/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        try:
            profile = Profile.objects.get(user=user)
            user_data = {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "profile": {
                    "role": profile.role,
                    "shop_name": profile.shop_name,
                    "bio": profile.bio,
                },
            }
            return Response(user_data)
        except Profile.DoesNotExist:
            return Response(
                {"error": "Profile not found."},
                status=status.HTTP_404_NOT_FOUND
            )
    
class RegisterView(APIView):
    """
    Register a new user account
    POST /api/register/
    """
    def post(self, request):
        username = request.data.get("username")
        email = request.data.get("email")
        password = request.data.get("password")
        role = request.data.get("role", "customer")
        shop_name = request.data.get("shop_name")
        bio = request.data.get("bio")

        # Validation
        if not username or not email or not password:
            return Response(
                {"error": "Username, email, and password are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if len(password) < 8:
            return Response(
                {"error": "Password must be at least 8 characters long."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if User.objects.filter(username=username).exists():
            return Response(
                {"error": "Username already exists."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if User.objects.filter(email=email).exists():
            return Response(
                {"error": "Email already in use."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if role not in ["customer", "vendor", "shop_admin"]:
            return Response(
                {"error": "Invalid role. Choose 'customer', 'vendor', or 'shop_admin'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if role == "vendor" and not shop_name:
            return Response(
                {"error": "Shop name is required for vendors."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Create user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )
            user.role = role  # Attach the role to the user instance
            user.save()

            # Explicitly create the profile with the correct role
            profile = Profile.objects.create(
                user=user,
                role=role,
                shop_name=shop_name if role in ["vendor", "shop_admin"] else None,
                bio=bio if role in ["vendor", "shop_admin"] else None,
            )
            
            return Response(
                {
                    "message": "Account created successfully.",
                    "user": UserSerializer(user).data
                },
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
@api_view(["GET"])
def get_all_customers(request):
    """
    Get all customers in the system
    """
    # Ensure only shop_admins can access this endpoint
    if not request.user.profile.role == "shop_admin":
        return Response({"error": "Permission denied."}, status=403)

    # Fetch all customers
    customers = Profile.objects.filter(role="customer").select_related("user")
    customer_data = [
        {
            "id": customer.user.id,
            "username": customer.user.username,
            "email": customer.user.email,
            "is_active": customer.user.is_active,
        }
        for customer in customers
    ]

    # Metrics: Total number of customers
    total_customers = customers.count()

    return Response({"total_customers": total_customers, "customers": customer_data})

@api_view(["POST"])
def block_or_restore_customer(request, user_id):
    """
    Block or restore a customer account
    """
    # Ensure only shop_admins can access this endpoint
    if not request.user.profile.role == "shop_admin":
        return Response({"error": "Permission denied."}, status=403)

    try:
        user = User.objects.get(id=user_id)
        if user.profile.role != "customer":
            return Response({"error": "Only customers can be blocked or restored."}, status=400)

        # Toggle the is_active status
        user.is_active = not user.is_active
        user.save()

        status = "blocked" if not user.is_active else "restored"
        return Response({"message": f"Customer account has been {status}."})
    except User.DoesNotExist:
        return Response({"error": "User not found."}, status=404)
    
@api_view(["GET"])
def get_all_vendors(request):
    """
    Get all vendors in the system
    """
    # Ensure only shop_admins or vendors can access this endpoint
    if not request.user.profile.role in ["shop_admin", "vendor"]:
        return Response({"error": "Permission denied."}, status=403)

    # Fetch all vendors
    vendors = Profile.objects.filter(role="vendor").select_related("user")
    vendor_data = [
        {
            "id": vendor.user.id,
            "username": vendor.user.username,
            "email": vendor.user.email,
            "is_active": vendor.user.is_active,
        }
        for vendor in vendors
    ]

    # Metrics: Total number of vendors
    total_vendors = vendors.count()

    return Response({"total_vendors": total_vendors, "vendors": vendor_data})

@api_view(["POST"])
def block_or_restore_vendor(request, user_id):
    """
    Block or restore a vendor account
    """
    # Ensure only shop_admins can access this endpoint
    if not request.user.profile.role == "shop_admin":
        return Response({"error": "Permission denied."}, status=403)

    try:
        user = User.objects.get(id=user_id)
        if user.profile.role != "vendor":
            return Response({"error": "Only vendors can be blocked or restored."}, status=400)

        # Toggle the is_active status
        user.is_active = not user.is_active
        user.save()

        status = "blocked" if not user.is_active else "restored"
        return Response({"message": f"Vendor account has been {status}."})
    except User.DoesNotExist:
        return Response({"error": "User not found."}, status=404)
    
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_product(request):
    """
    Create a new product
    """
    user = request.user

    # Ensure only vendors can create products
    if not user.profile.role == "vendor":
        return Response({"error": "Only vendors can create products."}, status=403)

    # Extract product data from the request
    name = request.data.get("name")
    description = request.data.get("description")
    price = request.data.get("price")
    stock = request.data.get("stock")
    category_id = request.data.get("category")
    weight = request.data.get("weight", 2.0)
    material_type = request.data.get("material_type")
    transport_distance = request.data.get("transport_distance", 2.0)
    transport_mode = request.data.get("transport_mode", "truck")
    energy_usage = request.data.get("energy_usage", 2.0)
    grid_intensity = request.data.get("grid_intensity", 0.2)
    longevity = request.data.get("longevity", 50)

    # Validate required fields
    if not all([name, price, stock, category_id, material_type, transport_mode]):
        return Response({"error": "Missing required fields."}, status=400)


    # Validate material_type and transport_mode
    valid_material_types = [
        "recycled_polyester", "virgin_polyester", "organic_cotton", "conventional_cotton",
        "linen", "hemp", "wool", "nylon", "silk", "recycled_cardboard", "virgin_paper",
        "recycled_plastic_pet", "virgin_plastic_pet", "bioplastic_pla", "glass",
        "aluminum_recycled", "aluminum_virgin", "steel", "copper", "lithium_ion_battery",
        "bamboo", "cork", "hardwood_timber", "concrete"
    ]
    valid_transport_modes = ["air", "truck", "sea"]

    if material_type not in valid_material_types:
        return Response({"error": "Invalid material type."}, status=400)

    if transport_mode not in valid_transport_modes:
        return Response({"error": "Invalid transport mode."}, status=400)

    # Validate the data
    if not name or not price or not stock:
        return Response(
            {"error": "Name, price, stock and category are required fields."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Fetch the category
        category = Category.objects.get(id=category_id)
        
        # Create the product
        product = Product.objects.create(
            name=name,
            description=description,
            price=price,
            stock=stock,
            category=category,  # Associate the product with the selected category
            vendor=user,  # Associate the product with the logged-in vendor
            weight=weight,
            material_type=material_type,
            transport_distance=transport_distance,
            transport_mode=transport_mode,
            energy_usage=energy_usage,
            grid_intensity=grid_intensity,
            longevity=longevity,
        )
        return Response(
            {"message": "Product created successfully.", "product": ProductSerializer(product).data},
            status=status.HTTP_201_CREATED,
        )
    except Category.DoesNotExist:
        return Response({"error": "Invalid category ID."}, status=400)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_vendor_products(request):
    """
    Get all products for the logged-in vendor
    """
    user = request.user

    # Ensure the user is a vendor
    if not user.profile.role == "vendor":
        return Response({"error": "Only vendors can view their products."}, status=403)

    # Fetch products for the vendor
    products = Product.objects.filter(vendor=user)
    product_data = [
        {
            "id": product.id,
            "name": product.name,
            "description": product.description,
            "price": product.price,
            "stock": product.stock,
        }
        for product in products
    ]

    return Response({"products": product_data})

@api_view(["GET"])
@permission_classes([AllowAny])
def get_categories(request):
    """
    Get all categories
    """
    categories = Category.objects.all()
    serializer = CategorySerializer(categories, many=True)
    return Response(serializer.data)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_to_cart(request):
    """
    Add a product to the cart or update its quantity
    """
    user = request.user
    product_id = request.data.get("product_id")
    quantity = request.data.get("quantity", 1)

    try:
        product = Product.objects.get(id=product_id)

        # Get or create the user's cart
        cart, created = Cart.objects.get_or_create(user=user)

        # Check if the product is already in the cart
        cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)

        if not created:
            # If the item already exists, update the quantity
            cart_item.quantity += int(quantity)
        else:
            cart_item.quantity = int(quantity)

        cart_item.save()

        return Response({"message": "Product added to cart successfully."}, status=200)
    except Product.DoesNotExist:
        return Response({"error": "Product not found."}, status=404)
    except Exception as e:
        return Response({"error": str(e)}, status=500)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def view_cart(request):
    """
    View the user's cart
    """
    user = request.user
    try:
        cart = Cart.objects.get(user=user)
        cart_items = cart.items.all()
        data = [
            {
                "product": {
                    "id": item.product.id,
                    "name": item.product.name,
                    "price": item.product.price,
                },
                "quantity": item.quantity,
            }
            for item in cart_items
        ]
        return Response({"cart": data}, status=200)
    except Cart.DoesNotExist:
        return Response({"cart": []}, status=200)
    
@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_cart_item_quantity(request):
    """
    Update the quantity of a cart item
    """
    user = request.user
    product_id = request.data.get("product_id")
    quantity = request.data.get("quantity")

    if quantity < 1:
        return Response({"error": "Quantity must be at least 1."}, status=400)

    try:
        cart = Cart.objects.get(user=user)
        cart_item = CartItem.objects.get(cart=cart, product_id=product_id)
        cart_item.quantity = quantity
        cart_item.save()

        return Response({"message": "Cart item updated successfully."}, status=200)
    except Cart.DoesNotExist:
        return Response({"error": "Cart not found."}, status=404)
    except CartItem.DoesNotExist:
        return Response({"error": "Cart item not found."}, status=404)
    except Exception as e:
        return Response({"error": str(e)}, status=500)

@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def clear_cart(request):
    """
    Clear all items from the user's cart.
    """
    user = request.user
    try:
        # Get the user's cart
        cart = Cart.objects.get(user=user)
        # Delete all items in the cart
        CartItem.objects.filter(cart=cart).delete()
        return Response({"message": "Cart cleared successfully"}, status=200)
    except Cart.DoesNotExist:
        return Response({"error": "Cart not found"}, status=404)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_order(request):
    """
    Create an order for the authenticated user.
    """
    user = request.user
    data = request.data

    # Extract order details from the request
    address = data.get("address")
    delivery_option = data.get("deliveryOption")
    cart_items = data.get("cart")
    total_cost = data.get("totalCost")

    if not address or not cart_items:
        return Response({"error": "Invalid order data"}, status=400)

    # Create the order
    order = Order.objects.create(
        user=user,
        full_name=address["fullName"],
        street=address["street"],
        city=address["city"],
        region=address["region"],
        post_code=address["postCode"],
        country=address["country"],
        delivery_option=delivery_option,
        total_cost=total_cost,
    )

    # Create order items
    for item in cart_items:
        product = item["product"]
        OrderItem.objects.create(
            order=order,
            product_id=product["id"],
            price=product["price"],
            quantity=item["quantity"],
        )

    # Clear the user's cart
    CartItem.objects.filter(cart__user=user).delete()

    return Response({"message": "Order created successfully", "orderId": order.id}, status=201)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def view_orders(request):
    """
    Fetch all orders for the authenticated user.
    """
    user = request.user
    # Fetch orders and "select_related" to optimize database hits
    orders = Order.objects.filter(user=user).order_by("-created_at")

    data = [
        {
            "id": order.id,
            "created_at": order.created_at,
            "total_cost": float(order.total_cost), # 1. Convert Decimal to float for JSON
            "status": order.status,
            "items": [
                {
                    # 2. FIX: Pull name from the Product, not the OrderItem
                    "name": item.product.name, 
                    "price": float(item.price),
                    "quantity": item.quantity,
                }
                # 3. FIX: Use the correct related_name (usually 'items' or 'orderitem_set')
                for item in order.items.all() 
            ],
        }
        for order in orders
    ]

    return Response(data, status=200)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def customer_dashboard(request):
    """
    Fetch dashboard metrics for the authenticated user.
    """
    user = request.user

    # Fetch orders with related data
    orders = Order.objects.filter(user=user).prefetch_related('items__product')

    # Total CO2 saved
    total_co2_saved = sum(
        item.product.co2_saved * item.quantity
        for order in orders
        for item in order.items.all()
    )

    # Number of EcoPurchases
    eco_purchases = orders.count()

    # Average EcoScore
    eco_scores = [
        item.product.eco_score
        for order in orders
        for item in order.items.all()
    ]
    average_eco_score = sum(eco_scores) / len(eco_scores) if eco_scores else 0

    # CO2 savings over time
    co2_savings_over_time = (
        Order.objects.filter(user=user)
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(total_co2_saved=Sum(F("items__quantity") * F("items__product__co2_saved")))
        .order_by("month")
    )

    # Recent purchases
    recent_orders = orders.order_by("-created_at")[:5]
    recent_purchases = [
        {
            "id": order.id,
            "created_at": order.created_at,
            "total_cost": order.total_cost,
            "items": [
                {
                    "name": item.product.name,
                    "price": item.price,
                    "quantity": item.quantity,
                }
                for item in order.items.all()
            ],
        }
        for order in recent_orders
    ]

    return Response({
        "total_co2_saved": total_co2_saved,
        "eco_purchases": eco_purchases,
        "average_eco_score": average_eco_score,
        "co2_savings_over_time": list(co2_savings_over_time),
        "recent_purchases": recent_purchases,
    }, status=200)





