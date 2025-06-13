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

### 🔄 In Progress Tasks

### ⏳ Pending Tasks

#### 1.1 Create BaseExporter Abstract Class
**File**: `src/prefect_data_getters/exporters/base.py`
- [ ] Create abstract `BaseExporter` class with `export()` method
- [ ] Add common utility methods for authentication and error handling
- [ ] Include proper type hints and docstrings
- [ ] Add configuration support via optional config parameter

**Acceptance Criteria**:
- Abstract class cannot be instantiated directly
- `export()` method is abstract and must be implemented by subclasses
- Includes comprehensive docstrings with Google style
- Type hints for all methods and parameters

#### 1.2 Create Processing Functions in Exporters Module
**File**: `src/prefect_data_getters/exporters/__init__.py`
- [ ] Implement `add_ingestion_timestamp()` with configurable metadata field
- [ ] Implement `convert_to_ai_documents()` function using existing DocumentTypeRegistry
- [ ] Add utility functions for common document transformations
- [ ] Add proper error handling and logging
- [ ] Include comprehensive type hints
- [ ] Use absolute imports throughout

**Function Signatures**:
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

**Acceptance Criteria**:
- Functions work with any Iterator[Document]
- Configurable metadata field name for timestamp function
- Integration with existing DocumentTypeRegistry for conversion
- Preserves all existing document metadata
- Handles edge cases (None metadata, empty documents)
- Uses absolute imports: `from prefect_data_getters.stores.document_registry import DocumentTypeRegistry`

#### 1.3 Set Up Testing Framework
**Directory**: `tests/exporters/`
- [ ] Create test structure mirroring main code
- [ ] Write unit tests for BaseExporter (test that it's abstract)
- [ ] Write unit tests for processing functions in exporters/__init__.py
- [ ] Set up pytest configuration and fixtures

**Test Coverage Requirements**:
- Expected use case tests
- Edge case tests (empty iterators, None values)
- Failure case tests (invalid data, network errors)
- Integration tests with existing stores module

## Phase 2: Refactor Gmail Exporter (Week 2)

### ⏳ Pending Tasks

#### 2.1 Refactor Gmail Exporter
**File**: `src/prefect_data_getters/exporters/gmail.py`
- [ ] Create `GmailExporter` class inheriting from `BaseExporter`
- [ ] Implement specific `export()` method signature with Gmail parameters
- [ ] Extract authentication logic into separate methods
- [ ] Move existing functionality from `gmail/__init__.py`
- [ ] Add comprehensive error handling and retry logic

**Method Signature**:
```python
def export(
    self, 
    days_ago: int = 7, 
    query: str = None, 
    max_results: int = None
) -> Iterator[Document]:
```

**Acceptance Criteria**:
- Inherits from BaseExporter
- Specific method signature for IDE code completion
- Maintains all existing functionality
- Improved error handling and logging
- Memory efficient (uses iterators)

#### 2.2 Update Gmail Module Structure
**File**: `src/prefect_data_getters/exporters/gmail/__init__.py`
- [ ] Update to import from new `gmail.py` module
- [ ] Maintain backward compatibility with existing functions
- [ ] Add deprecation warnings for old functions
- [ ] Provide migration examples in docstrings
- [ ] Use absolute imports

#### 2.3 Create Gmail-Specific Tests
**File**: `tests/exporters/test_gmail.py`
- [ ] Test Gmail exporter instantiation and inheritance
- [ ] Test export method with various parameters
- [ ] Mock Gmail API calls for testing
- [ ] Test error handling and edge cases
- [ ] Test backward compatibility functions
- [ ] Test integration with processing functions from exporters module

## Phase 3: Refactor Other Exporters (Week 3)

### ⏳ Pending Tasks

#### 3.1 Refactor Slack Exporter
**File**: `src/prefect_data_getters/exporters/slack.py`
- [ ] Create `SlackExporter` class inheriting from `BaseExporter`
- [ ] Implement specific export method signature
- [ ] Move logic from existing slack modules
- [ ] Add Slack-specific error handling

**Method Signature**:
```python
def export(
    self, 
    channels: List[str] = None, 
    days_ago: int = 7, 
    limit: int = None
) -> Iterator[Document]:
```

#### 3.2 Refactor Jira Exporter
**File**: `src/prefect_data_getters/exporters/jira.py`
- [ ] Create `JiraExporter` class inheriting from `BaseExporter`
- [ ] Implement specific export method signature
- [ ] Add Jira-specific authentication and error handling

**Method Signature**:
```python
def export(
    self, 
    project: str = None, 
    status: str = None, 
    assignee: str = None
) -> Iterator[Document]:
```

#### 3.3 Refactor Remaining Exporters
- [ ] **Slab Exporter**: `src/prefect_data_getters/exporters/slab.py`
- [ ] **Bitbucket Exporter**: `src/prefect_data_getters/exporters/bitbucket.py`
- [ ] **Calendar Exporter**: `src/prefect_data_getters/exporters/calendar.py`

#### 3.4 Create Source-Specific Processing
**Directory**: `src/prefect_data_getters/processing/custom/`
- [ ] **Slack Processing**: `slack.py` - extend slack message context
- [ ] **Jira Processing**: `jira.py` - enrich Jira metadata
- [ ] Add tests for custom processing functions

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