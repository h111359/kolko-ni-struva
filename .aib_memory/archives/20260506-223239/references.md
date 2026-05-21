| ref_id | title | path | type | edit_allowed | source | notes |
| --- | --- | --- | --- | --- | --- | --- |
| REF-0001 | AIB Context | .aib_memory/context.md | product-doc | Y | default | Unified workspace context synthesized by aib-context.md |
| REF-0002 | AIB Concepts | .aib_brain\Concepts.md | domain | N | user | This document describes the concepts for AI Builder |
Validation rules:
- `ref_id` unique, format `REF-0001`.
- `path` unique and workspace-relative.
- `type` in `product-doc|source-code|domain|other`.
- `edit_allowed` in `Y|N`.
- `source` in `default|user`.