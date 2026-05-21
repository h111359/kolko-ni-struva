# Coding Django Convention

**Scope:** Normative  
**Applies to:** All Python files (`.py`) that are part of a Django web application, including views, models, serializers, URL configurations, forms, signals, management commands, and settings, created or edited by the AI Automation Agent during any `implement` workflow run.  
**Extends:** `coding-general-convention.md` and `coding-python-convention.md` — all rules defined in both MUST be applied in addition to the rules below.

---

## 1. Purpose

This convention defines Django-specific commenting and code-quality rules for AI-generated Django application code. It ensures that views, models, serializers, and URL routing are clearly documented for developers working on Django projects.

---

## 2. Scope & Normative Language

This convention applies to:

- Django view files (function-based and class-based views).
- Django model files.
- Django REST Framework or Ninja serializer and API view files.
- URL configuration files (`urls.py`).
- Django form files.
- Django signal files.
- Django management command files.

Out of scope:
- Django migration files (`migrations/*.py`) — auto-generated files, comment rules do not apply.
- Flask-specific files — apply `coding-flask-convention.md`.

Normative keywords **MUST**, **MUST NOT**, **SHALL**, **SHOULD**, and **MAY** are interpreted per BCP 14 (RFC 2119 / RFC 8174).

---

## 3. File-Level Header

Every Django file MUST begin with a module-level docstring (per `coding-python-convention.md`) that additionally specifies:

- The Django application (app) the file belongs to.
- The type of Django artifact (views, models, serializers, etc.).

Example:

```python
"""
catalog/models.py: Django ORM model definitions for the product catalog application.
App: catalog
Contains: Product, Category, ProductImage models.
"""
```

---

## 4. Model Documentation

Every Django model class MUST have a docstring that describes:

- The real-world entity or concept the model represents.
- Key relationships (ForeignKey, ManyToManyField) and what they represent.
- Any important constraints or business rules enforced at the model level.

Every model field MUST have a `help_text` argument OR an inline comment in the field definition that explains the field's business meaning.

Example:

```python
class Product(models.Model):
    """
    Represents a sellable product in the catalog.

    Relationships:
        category (ForeignKey -> Category): The product's primary classification.
        images (ManyToMany -> ProductImage): Associated product images.

    Constraints:
        price must be non-negative (enforced by MinValueValidator).
    """
    name = models.CharField(max_length=255, help_text="Display name shown to customers.")
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        # Price in USD; must be >= 0; enforced by validators in clean()
        validators=[MinValueValidator(Decimal("0.00"))]
    )
```

---

## 5. View Documentation

Every class-based view MUST have a class docstring describing:

- The resource or action the view serves.
- The HTTP methods handled and what each does.
- Required permissions or authentication constraints.

Every function-based view MUST have a function docstring with the same content.

---

## 6. URL Configuration Comments

Every URL pattern in `urls.py` MUST have an inline `#` comment describing the view it routes to and the HTTP action it enables.

URL namespaces MUST be documented with a comment at the top of the`urlpatterns` list.

---

## 7. Serializer Documentation

Every Django REST Framework or equivalent serializer class MUST have a docstring describing:

- The model or data structure it serializes.
- Any read-only, write-only, or computed fields and the reason for their special handling.
- Validation methods (`validate_<field>`, `validate`) MUST have docstrings describing the business rule being enforced.

---

## 8. Settings Documentation

Every non-standard or project-specific setting in `settings.py` or settings modules MUST have a comment explaining:

- The reason the setting is present.
- The acceptable values and their effects.
- Any security implications.

---

## 9. Code Quality Rules

- Views MUST NOT contain database query logic beyond ORM calls; business logic MUST be in services or model methods with docstrings.
- Raw SQL queries (`RawQuerySet`, `connection.cursor()`) MUST have a comment explaining why the ORM cannot satisfy the requirement.
- `select_related` and `prefetch_related` calls MUST be commented with the performance optimization they address.
- Signal receivers MUST have a docstring explaining the signal they respond to, the sender, and the side effect they produce.
- `settings.SECRET_KEY`, `settings.DATABASES`, and other sensitive settings MUST NOT be hardcoded; a comment MUST indicate the environment variable or secrets manager key from which the value is loaded.
