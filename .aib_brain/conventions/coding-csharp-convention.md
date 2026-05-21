# Coding C# Convention

**Scope:** Normative  
**Applies to:** All C# source files (`.cs`) created or edited by the AI Automation Agent during any `implement` workflow run, including application code, test code, and configuration classes.  
**Extends:** `coding-general-convention.md` — all rules defined there MUST be applied in addition to the rules below.

---

## 1. Purpose

This convention defines C#-specific commenting and code-quality rules for AI-generated C# code. It ensures that classes, methods, properties, and interfaces are self-documented using idiomatic XML documentation comments consistent with .NET conventions.

---

## 2. Scope & Normative Language

This convention applies to:

- All `.cs` files created or modified by the AI Automation Agent.
- Application code, test code, and auto-generated partial classes that are edited manually.

Out of scope:
- Auto-generated scaffold files (e.g., EF Core migrations, scaffolded controllers) where the AI does not write substantive logic.
- Designer-generated files (`*.Designer.cs`) — comment rules do not apply.

Normative keywords **MUST**, **MUST NOT**, **SHALL**, **SHOULD**, and **MAY** are interpreted per BCP 14 (RFC 2119 / RFC 8174).

---

## 3. File-Level Header

Every C# file MUST begin with a file-level block comment header (using `//`) that states:

- The file name and a one-sentence description of the file's purpose.
- The primary namespace and the class or set of types defined.

Example:

```csharp
// RequestRepository.cs: Repository implementation for persisting and retrieving AIB requests.
// Namespace: AibCore.Data
// Defines: RequestRepository (implements IRequestRepository)
```

---

## 4. XML Documentation Comments

Every public class, interface, struct, enum, method, property, and event MUST have an XML documentation comment (`/// <summary>`) immediately above its declaration.

The `<summary>` element MUST describe what the member is or does in one to three sentences.

Methods MUST additionally include:

- `<param name="...">` for every parameter.
- `<returns>` for every non-void method.
- `<exception cref="...">` for every explicitly thrown or documented exception.

Example:

```csharp
/// <summary>
/// Retrieves a registered AIB request by its unique identifier.
/// Returns null if no request with the specified ID exists.
/// </summary>
/// <param name="requestId">The unique request identifier in the format R-YYYYMMDD-HHMM.</param>
/// <returns>The <see cref="Request"/> instance if found; otherwise null.</returns>
/// <exception cref="ArgumentNullException">Thrown when <paramref name="requestId"/> is null or empty.</exception>
public Request? GetById(string requestId)
```

Internal members (e.g., `internal` or `private`) SHOULD have XML documentation or at minimum an inline `//` comment when their purpose is non-obvious.

---

## 5. Interface Documentation

Every interface MUST have an XML `<summary>` describing the contract it defines (not the implementing class).

Interface members MUST each have their own `<summary>` tags with parameter and return documentation.

---

## 6. Inline Comments

Inline `//` comments MUST be used for:

- LINQ queries with non-obvious projection logic — comment the intent of the query, not the syntax.
- Null coalescing, null-forgiving (`!`) and nullable reference type annotations — comment why nullability is handled as it is.
- `async/await` continuations where the threading context matters.

---

## 7. Constants and Enumerations

Every `const` or `readonly static` field MUST have an XML `<summary>` or an inline `//` comment explaining the constant's meaning and valid value range.

Every enum value MUST have an XML `<summary>` comment.

---

## 8. Exception Handling

Every `catch` block MUST have a comment explaining what exception condition is being handled and why.

Rethrowing exceptions using `throw;` (not `throw ex;`) is the REQUIRED pattern; any deviation MUST be commented with the reason.

Empty `catch` blocks are PROHIBITED without a comment explaining why the exception is intentionally swallowed.

---

## 9. Code Quality Rules

- Methods MUST NOT exceed 40 lines of executable code; decompose into private helper methods with XML documentation.
- Magic string literals and numeric literals MUST be extracted to named constants with documentation comments.
- `#region` blocks are PROHIBITED; use partial classes or refactoring to manage file complexity.
- `dynamic` types MUST have a comment explaining why static typing cannot be applied.
- `TODO` and `FIXME` comments MUST follow the format in `coding-general-convention.md` Section 6.
