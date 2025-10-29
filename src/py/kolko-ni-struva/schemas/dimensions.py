"""
Dimension schema definitions using dataclasses.

This module defines the structure of all dimension types used in the
normalized data model.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Category:
    """
    Product category dimension.
    
    Attributes:
        category_id: Unique identifier
        name: Category name in Bulgarian
    """
    category_id: int
    name: str


@dataclass
class City:
    """
    City/settlement dimension with EKATTE codes.
    
    Attributes:
        city_id: Unique identifier
        ekatte_code: 5-digit EKATTE code (normalized)
        name: City name in Bulgarian
    """
    city_id: int
    ekatte_code: str
    name: str


@dataclass
class TradeChain:
    """
    Retail trade chain dimension.
    
    Attributes:
        chain_id: Unique identifier (matches source account ID)
        name: Trade chain name
    """
    chain_id: int
    name: str


@dataclass
class TradeObject:
    """
    Individual trade object/shop dimension.
    
    Attributes:
        object_id: Unique identifier
        chain_id: Foreign key to TradeChain
        address: Shop address/location
    """
    object_id: int
    chain_id: int
    address: str


@dataclass
class Product:
    """
    Product dimension with category relationship.
    
    Attributes:
        product_id: Unique identifier
        name: Product name
        product_code: Source product code (may be empty)
        category_id: Foreign key to Category
    """
    product_id: int
    name: str
    product_code: Optional[str]
    category_id: int


@dataclass
class PriceFact:
    """
    Price fact table row.
    
    Attributes:
        date: Observation date (ISO format YYYY-MM-DD)
        trade_chain_id: Foreign key to TradeChain
        trade_object_id: Foreign key to TradeObject
        city_id: Foreign key to City
        product_id: Foreign key to Product
        category_id: Foreign key to Category
        retail_price: Regular retail price in BGN (nullable)
        promo_price: Promotional price in BGN (nullable)
    """
    date: str
    trade_chain_id: int
    trade_object_id: int
    city_id: int
    product_id: int
    category_id: int
    retail_price: Optional[float]
    promo_price: Optional[float]
