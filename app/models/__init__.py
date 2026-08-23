"""Modelos SQLAlchemy de eServicios.

Catálogo de productos, servicios, cursos y consultorías (dossier), con
soporte de carrito/checkout (Order/OrderItem), panel de administración
(AdminUser), y tiendas de vendedor con subdominio propio
(Vendor/VendorProduct/VendorLink, estilo Linktree/Beacons — ver
`claude/spec-tiendas-vendedor.md` en el proyecto). Los modelos de
marketplace (candidatos, empleadores, vacantes) quedaron pendientes
para el proyecto Polunga.
"""
from app.models.admin_user import AdminUser, RolAdmin
from app.models.blog_post import BlogPost, EstadoBlogPost
from app.models.category import Category
from app.models.lead import Lead
from app.models.offering import Offering, TipoOffering
from app.models.offering_foto import OfferingFoto
from app.models.order import EstadoOrder, Order, OrderItem
from app.models.reserved_slug import ReservedSlug
from app.models.testimonial import Testimonial
from app.models.vendor import PlanVendor, Vendor
from app.models.vendor_link import VendorLink
from app.models.vendor_product import VendorProduct
from app.models.vendor_product_foto import VendorProductFoto

__all__ = [
    "AdminUser",
    "RolAdmin",
    "BlogPost",
    "EstadoBlogPost",
    "Category",
    "Lead",
    "Offering",
    "TipoOffering",
    "OfferingFoto",
    "Order",
    "OrderItem",
    "EstadoOrder",
    "ReservedSlug",
    "Testimonial",
    "Vendor",
    "PlanVendor",
    "VendorLink",
    "VendorProduct",
    "VendorProductFoto",
]
