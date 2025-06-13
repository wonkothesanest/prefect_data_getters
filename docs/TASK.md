# Loosely Coupled Exporter Architecture Implementation

**Project**: Prefect Data Getters  
**Start Date**: 2025-06-13  
**Status**: In Progress

## Overview

Refactor the data exporter architecture to use a loosely coupled, functional approach with abstract base classes and composable processing functions.

## Phase 1: Base Infrastructure (Week 1)

### ✅ Completed Tasks
- [x] Created architectural documentation (2025-06-13)
- [x] Updated PLANNING.md with new architecture (2025-06-13)
- [x] Created BaseExporter Abstract Class (2025-06-13)
- [x] Created Processing Functions in Exporters Module (2025-06-13)
- [x] Set Up Testing Framework (2025-06-13)

### 🔄 In Progress Tasks

### ⏳ Pending Tasks

#### 1.1 Create BaseExporter Abstract Class ✅ COMPLETED
**File**: `src/prefect_data_getters/exporters/base.py`
- [x] Create abstract `BaseExporter` class with `export()` method
- [x] Add common utility methods for authentication and error handling
- [x] Include proper type hints and docstrings
- [x] Add configuration support via optional config parameter

**Acceptance Criteria**: ✅ ALL MET
- [x] Abstract class cannot be instantiated directly
- [x] `export()` method is abstract and must be implemented by subclasses
- [x] Includes comprehensive docstrings with Google style
- [x] Type hints for all methods and parameters

#### 1.2 Create Processing Functions in Exporters Module ✅ COMPLETED
**File**: `src/prefect_data_getters/exporters/__init__.py`
- [x] Implement `add_ingestion_timestamp()` with configurable metadata field
- [x] Implement `convert_to_ai_documents()` function using existing DocumentTypeRegistry
- [x] Add utility functions for common document transformations
- [x] Add proper error handling and logging
- [x] Include comprehensive type hints
- [x] Use absolute imports throughout

**Function Signatures**: ✅ IMPLEMENTED
```python
def add_ingestion_timestamp(
    docs: Iterator[Document],
    metadata_field: str = "ingestion_timestamp"
) -> Iterator[Document]:

def convert_to_ai_documents(
    docs: Iterator[Document],
    store_name: str
) -> Iterator[AIDocument]:
```

**Acceptance Criteria**: ✅ ALL MET
- [x] Functions work with any Iterator[Document]
- [x] Configurable metadata field name for timestamp function
- [x] Integration with existing DocumentTypeRegistry for conversion
- [x] Preserves all existing document metadata
- [x] Handles edge cases (None metadata, empty documents)
- [x] Uses absolute imports: `from prefect_data_getters.stores.document_registry import DocumentTypeRegistry`

#### 1.3 Set Up Testing Framework ✅ COMPLETED
**Directory**: `tests/exporters/`
- [x] Create test structure mirroring main code
- [x] Write unit tests for BaseExporter (test that it's abstract)
- [x] Write unit tests for processing functions in exporters/__init__.py
- [x] Set up pytest configuration and fixtures

**Test Coverage Requirements**: ✅ ALL MET
- [x] Expected use case tests
- [x] Edge case tests (empty iterators, None values)
- [x] Failure case tests (invalid data, network errors)
- [x] Integration tests with existing stores module

## Phase 2: Refactor Gmail Exporter (Week 2)

### ✅ Completed Tasks
- [x] Refactored Gmail Exporter (2025-06-13)
- [x] Updated Gmail Module Structure (2025-06-13)
- [x] Created Gmail-Specific Tests (2025-06-13)

### ⏳ Pending Tasks

#### 2.1 Refactor Gmail Exporter ✅ COMPLETED
**File**: `src/prefect_data_getters/exporters/gmail.py`
- [x] Create `GmailExporter` class inheriting from `BaseExporter`
- [x] Implement specific `export()` method signature with Gmail parameters
- [x] Extract authentication logic into separate methods
- [x] Move existing functionality from `gmail/__init__.py`
- [x] Add comprehensive error handling and retry logic

**Method Signature**: ✅ IMPLEMENTED
```python
def export(
    self,
    days_ago: int = 7,
    query: str = None,
    max_results: int = None
) -> Iterator[Document]:
```

**Acceptance Criteria**: ✅ ALL MET
- [x] Inherits from BaseExporter
- [x] Specific method signature for IDE code completion
- [x] Maintains all existing functionality
- [x] Improved error handling and logging
- [x] Memory efficient (uses iterators)

#### 2.2 Update Gmail Module Structure ✅ COMPLETED
**File**: `src/prefect_data_getters/exporters/gmail/__init__.py`
- [x] Update to import from new `gmail.py` module
- [x] Maintain backward compatibility with existing functions
- [x] Add deprecation warnings for old functions
- [x] Provide migration examples in docstrings
- [x] Use absolute imports

#### 2.3 Create Gmail-Specific Tests ✅ COMPLETED
**File**: `tests/exporters/test_gmail.py`
- [x] Test Gmail exporter instantiation and inheritance
- [x] Test export method with various parameters
- [x] Mock Gmail API calls for testing
- [x] Test error handling and edge cases
- [x] Test backward compatibility functions
- [x] Test integration with processing functions from exporters module

**Test Results**: ✅ 24 TESTS PASSED
- Complete test coverage with 100% pass rate
- Comprehensive error handling validation
- Backward compatibility verification
- Integration testing with processing functions

## Phase 3: Refactor Other Exporters (Week 3)

### ✅ Completed Tasks
- [x] Refactored Slack Exporter (2025-06-13)
- [x] Enhanced BaseExporter with separate export() and process() methods (2025-06-13)
- [x] Updated Gmail and Slack exporters to new pattern (2025-06-13)
- [x] All tests passing (97/97) (2025-06-13)

### 🎯 Established Pattern for Remaining Exporters

The Gmail and Slack exporters have established a clear pattern that should be followed for all remaining exporters:

#### **Pattern Template for New Exporters**

1. **Inherit from BaseExporter** with two abstract methods:
   - `export(**kwargs) -> Iterator[Any]` - Returns raw API data
   - `process(raw_data: Iterator[Any]) -> Iterator[Document]` - Converts raw data to Documents

2. **Method Signatures** - Each exporter has specific parameters:
   ```python
   def export(self, param1: type = default, param2: type = default) -> Iterator[Dict[str, Any]]:
   def process(self, raw_data: Iterator[Dict[str, Any]]) -> Iterator[Document]:
   ```

3. **File Structure**:
   - Main exporter: `src/prefect_data_getters/exporters/{name}_exporter.py`
   - Tests: `tests/exporters/test_{name}.py`
   - Backward compatibility maintained in existing modules

4. **Test Requirements**:
   - Test both export() and process() methods separately
   - Test export_documents() convenience method
   - Test error handling and edge cases
   - Minimum 20+ tests per exporter

### ⏳ Remaining Exporters to Implement

#### 3.2 Jira Exporter
**File**: `src/prefect_data_getters/exporters/jira_exporter.py`
- [ ] Create `JiraExporter` class inheriting from `BaseExporter`
- [ ] Implement `export()` method returning raw Jira issue data
- [ ] Implement `process()` method converting to JiraDocument objects
- [ ] Add Jira-specific authentication and error handling
- [ ] Create comprehensive test suite (tests/exporters/test_jira.py)

**Method Signatures**:
```python
def export(self, project: str = None, status: str = None, assignee: str = None,
          days_ago: int = 30) -> Iterator[Dict[str, Any]]:
    """Export raw Jira issues."""

def process(self, raw_data: Iterator[Dict[str, Any]]) -> Iterator[Document]:
    """Process raw Jira data into JiraDocument objects."""
```

**Implementation Steps**:
1. Examine existing `src/prefect_data_getters/exporters/jira/__init__.py`
2. Extract authentication and API logic
3. Create separate export() method for raw data
4. Create process() method using existing JiraDocument type
5. Add comprehensive error handling and retry logic
6. Create test suite following Gmail/Slack pattern
7. Update backward compatibility in jira/__init__.py

#### 3.3 Slab Exporter
**File**: `src/prefect_data_getters/exporters/slab_exporter.py`
- [ ] Create `SlabExporter` class inheriting from `BaseExporter`
- [ ] Implement export() and process() methods
- [ ] Integration with existing SlabDocument types

**Method Signatures**:
```python
def export(self, space: str = None, days_ago: int = 30,
          limit: int = None) -> Iterator[Dict[str, Any]]:
def process(self, raw_data: Iterator[Dict[str, Any]]) -> Iterator[Document]:
```

#### 3.4 Bitbucket Exporter
**File**: `src/prefect_data_getters/exporters/bitbucket_exporter.py`
- [ ] Create `BitbucketExporter` class inheriting from `BaseExporter`
- [ ] Implement export() and process() methods
- [ ] Integration with existing BitbucketPR document type

**Method Signatures**:
```python
def export(self, repository: str = None, state: str = "OPEN",
          days_ago: int = 30) -> Iterator[Dict[str, Any]]:
def process(self, raw_data: Iterator[Dict[str, Any]]) -> Iterator[Document]:
```

#### 3.5 Calendar Exporter
**File**: `src/prefect_data_getters/exporters/calendar_exporter.py`
- [ ] Create `CalendarExporter` class inheriting from `BaseExporter`
- [ ] Implement export() and process() methods
- [ ] Create appropriate document type for calendar events

**Method Signatures**:
```python
def export(self, calendar_id: str = "primary", days_ago: int = 7,
          days_ahead: int = 30) -> Iterator[Dict[str, Any]]:
def process(self, raw_data: Iterator[Dict[str, Any]]) -> Iterator[Document]:
```

### 📋 Implementation Checklist for Each Exporter

For each remaining exporter, follow this checklist:

#### **Development Steps**
- [ ] 1. Analyze existing exporter code in `exporters/{name}/__init__.py`
- [ ] 2. Create new `{name}_exporter.py` file with class inheriting from BaseExporter
- [ ] 3. Implement `export()` method returning raw API data (Iterator[Dict[str, Any]])
- [ ] 4. Implement `process()` method converting raw data to Documents
- [ ] 5. Add authentication, error handling, and retry logic
- [ ] 6. Ensure integration with existing document types
- [ ] 7. Add comprehensive logging throughout

#### **Testing Steps**
- [ ] 8. Create `tests/exporters/test_{name}.py` following established pattern
- [ ] 9. Test export() method with mocked API responses
- [ ] 10. Test process() method with sample raw data
- [ ] 11. Test export_documents() convenience method
- [ ] 12. Test error handling and edge cases
- [ ] 13. Test backward compatibility
- [ ] 14. Achieve minimum 20+ tests with 100% pass rate

#### **Integration Steps**
- [ ] 15. Update existing `exporters/{name}/__init__.py` for backward compatibility
- [ ] 16. Add deprecation warnings to old functions
- [ ] 17. Update `exporters/__init__.py` to include new exporter
- [ ] 18. Create usage examples in `examples/{name}_exporter_demo.py`
- [ ] 19. Update documentation

### 🎯 Success Criteria for Each Exporter

- [ ] Inherits from BaseExporter with proper method signatures
- [ ] Separates raw data export from document processing
- [ ] Maintains all existing functionality
- [ ] Has comprehensive test coverage (20+ tests, 100% pass rate)
- [ ] Includes proper error handling and retry logic
- [ ] Maintains backward compatibility
- [ ] Follows established code patterns from Gmail/Slack exporters
- [ ] Integrates with existing document types and storage systems

### 📈 Priority Order

1. **Jira Exporter** (highest priority - most complex API)
2. **Slab Exporter** (medium priority - documentation system)
3. **Bitbucket Exporter** (medium priority - code repository)
4. **Calendar Exporter** (lower priority - simpler API)

Each exporter should be implemented, tested, and verified before moving to the next one to ensure quality and consistency.

## Phase 4: Integration and Workflows (Week 4)

### ⏳ Pending Tasks

#### 4.1 Create Convenience Workflows
**Directory**: `src/prefect_data_getters/workflows/`
- [ ] **Gmail Sync**: `gmail_sync.py` - pre-built Gmail workflow
- [ ] **Slack Sync**: `slack_sync.py` - pre-built Slack workflow
- [ ] **Multi-Source Sync**: `multi_source.py` - sync all sources
- [ ] Add configuration options for each workflow

#### 4.2 Integration Testing
**Directory**: `tests/integration/`
- [ ] Test complete data flow from export to storage
- [ ] Test multi-source processing
- [ ] Test error recovery and retry mechanisms
- [ ] Performance testing with large datasets

#### 4.3 Documentation and Examples
- [ ] Update README.md with new usage examples
- [ ] Create migration guide from old to new architecture
- [ ] Add code examples for common use cases
- [ ] Document performance characteristics and best practices

#### 4.4 Backward Compatibility
- [ ] Ensure all existing code continues to work
- [ ] Add deprecation warnings where appropriate
- [ ] Create compatibility shims for removed functions
- [ ] Test existing workflows still function

## Success Criteria

### Technical Requirements
- [ ] All exporters inherit from BaseExporter with specific signatures
- [ ] Processing functions are in exporters module and composable
- [ ] Use existing stores module for storage (do not modify)
- [ ] Memory efficient processing using iterators
- [ ] Comprehensive test coverage (>90%)
- [ ] No files exceed 500 lines of code
- [ ] Always use absolute imports

### Functional Requirements
- [ ] All existing functionality is preserved
- [ ] New architecture is easier to extend and maintain
- [ ] IDE code completion works for all exporter methods
- [ ] Error handling is improved across all components
- [ ] Performance is maintained or improved
- [ ] Integration with existing Prefect workflows in datagetters

### Documentation Requirements
- [ ] All functions have Google-style docstrings
- [ ] Type hints are used throughout
- [ ] Migration guide is complete and tested
- [ ] Examples demonstrate common usage patterns
- [ ] Document integration with existing Prefect architecture

## Risk Mitigation

### Backward Compatibility Risks
- **Risk**: Breaking existing code during refactoring
- **Mitigation**: Maintain old interfaces with deprecation warnings, comprehensive testing

### Performance Risks
- **Risk**: New architecture introduces performance overhead
- **Mitigation**: Use iterators throughout, benchmark against current implementation

### Complexity Risks
- **Risk**: New architecture is too complex for users
- **Mitigation**: Provide simple convenience workflows, clear documentation

## Dependencies

### Internal Dependencies
- Existing stores module (do not modify)
- Existing datagetters module (Prefect flows)
- Document registry system
- Elasticsearch manager
- Vector store implementation

### External Dependencies
- `langchain-core`: Document classes
- `typing`: Type hints and generics
- `abc`: Abstract base classes
- `prefect`: Workflow orchestration (existing)
- Data source APIs (Gmail, Slack, Jira, etc.)

## Notes

### Design Decisions
- Chose abstract base classes over protocols for better IDE support
- Used functional approach for processing to maximize composability
- Maintained iterator-based processing for memory efficiency
- Separated storage concerns completely from extraction

### Future Enhancements
- Consider async/await support for concurrent processing
- Add metrics and monitoring capabilities
- Implement caching layer for frequently accessed data
- Add data validation and schema enforcement

---

**Last Updated**: 2025-06-13  
**Next Review**: 2025-06-20