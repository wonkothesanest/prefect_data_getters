# AIDocument Refactoring Rules

## Overview

This document outlines a comprehensive refactoring plan to improve the maintainability, extensibility, and performance of the AIDocument system by:

1. **Inheriting from langchain_core.documents.Document** instead of wrapping it
2. **Eliminating the `_document` wrapper** and all pass-through methods
3. **Integrating Elasticsearch storage** directly into the document classes
4. **Simplifying the architecture** while maintaining all existing functionality

## Current Architecture Issues

### Problems Identified
- **Wrapper Complexity**: AIDocument wraps Document instead of inheriting from it
- **Duplication**: Properties like `id` and `page_content` are duplicated between wrapper and wrapped object
- **Pass-through Methods**: Methods like `set_page_content()` maintain synchronization between wrapper and wrapped
- **Separate Storage**: Elasticsearch integration is separate and works with raw dicts
- **Boilerplate Code**: Subclasses mostly differ only in `__str__` methods and ID extraction
- **Manual Type Management**: `_type_name` field is manually maintained when `__class__.__name__` could be used

### Current Flow
```
Raw Data → Document → AIDocument (wrapper) → Elasticsearch (separate)
```

## Proposed Architecture

### New Flow
```
Raw Data → AIDocument (inherits Document) → Elasticsearch (integrated)
```

### Core Design Principles
1. **Single Inheritance**: AIDocument extends Document directly
2. **Integrated Storage**: Elasticsearch operations built into document classes
3. **Type Introspection**: Use `__class__.__name__` instead of `_type_name`
4. **Registry Pattern**: Centralized document type management
5. **Unified Interface**: Single API for all document operations



# Planning and code writing rules
Always create a check list first in order to mana
