# Coding Flask Convention

**Scope:** Normative  
**Applies to:** All Python files (`.py`) that are part of a Flask web application, including routes, blueprints, forms, models, and application factory files, created or edited by the AI Automation Agent during any `implement` workflow run.  
**Extends:** `coding-general-convention.md` and `coding-python-convention.md` — all rules defined in both MUST be applied in addition to the rules below.

---

## 1. Purpose

This convention defines Flask-specific commenting and code-quality rules for AI-generated Flask application code. It ensures that route handlers, view functions, blueprints, and application configuration are clearly documented for web developers working on Flask projects.

---

## 2. Scope & Normative Language

This convention applies to:

- Flask route and view function files.
- Blueprint definition files.
- Application factory files (e.g., `create_app`, `app_factory`).
- Flask-WTF form definition files.
- Flask extension initialization and configuration files.

Out of scope:
- General Python utility files that do not contain Flask-specific constructs — apply `coding-python-convention.md` only.
- Django-specific files — apply `coding-django-convention.md`.

Normative keywords **MUST**, **MUST NOT**, **SHALL**, **SHOULD**, and **MAY** are interpreted per BCP 14 (RFC 2119 / RFC 8174).

---

## 3. File-Level Header

Every Flask file MUST begin with a module-level docstring (per `coding-python-convention.md`) that additionally specifies:

- The Flask blueprint or application component the file belongs to.
- The URL prefix or routing namespace if the file defines routes.

Example:

```python
"""
auth/routes.py: Authentication route handlers for the AIB web interface.
Blueprint: auth (url_prefix=/auth)
Handles: login, logout, password reset endpoints.
"""
```

---

## 4. Route Handler Documentation

Every Flask route handler function MUST have a docstring that describes:

- The HTTP method(s) the route accepts.
- The URL path and any path parameters.
- The request body or query parameters expected (if applicable).
- The response format (HTML template rendered or JSON structure returned).

Example:

```python
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """
    Handles user login for the web interface.

    GET:  Renders the login form template (auth/login.html).
    POST: Validates credentials via LoginForm; on success redirects to dashboard;
          on failure re-renders form with error message.

    Request body (POST, form-encoded):
        username (str): The user's registered email address.
        password (str): The user's plaintext password (hashed before comparison).

    Returns:
        Rendered template (GET/failed POST) or redirect response (successful POST).
    """
```

---

## 5. Blueprint Registration Comments

Every call to `app.register_blueprint()` MUST be accompanied by a comment stating the blueprint's purpose and its URL prefix.

---

## 6. Application Factory Comments

The application factory function (`create_app` or equivalent) MUST have a docstring describing:

- The configuration object or name it accepts.
- The extensions it initializes and in what order.
- The blueprints it registers.

---

## 7. Error Handler Documentation

Every `@app.errorhandler` or `@blueprint.errorhandler` decorated function MUST have a docstring explaining:

- The HTTP status code handled.
- The error condition that triggers it.
- The response returned.

---

## 8. Code Quality Rules

- Route handler functions MUST NOT contain business logic; logic MUST be delegated to service or model functions with their own docstrings.
- Template context dictionaries passed to `render_template` MUST have a comment listing the key names and their expected types when the dictionary has more than three keys.
- `current_app`, `g`, and `request` context globals used outside of a request context MUST be commented with a note explaining the usage pattern.
- Secret keys, API keys, and database connection strings MUST NOT be hardcoded; they MUST be loaded from environment variables or configuration, with a comment indicating where the value originates.
