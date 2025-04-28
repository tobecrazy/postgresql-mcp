# PostgreSQL MCP Server

A Model Context Protocol (MCP) server that provides CRUD operations for PostgreSQL database tables.

## Overview

This MCP server allows you to interact with PostgreSQL databases through a set of tools that provide Create, Read, Update, and Delete (CRUD) operations on specified tables. The server uses the FastMCP library and runs in stdio mode, making it compatible with various MCP clients.

## Features

- Connect to PostgreSQL databases
- Perform CRUD operations on specified tables
- Table and column-level access control
- Schema inspection
- Custom SQL query execution
- Configuration via YAML file

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/postgresql-mcp.git
   cd postgresql-mcp
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Configuration

The server is configured using the `config.yaml` file. This file contains:

1. Database connection details
2. Table configurations, including:
   - Which tables are accessible
   - Which columns are allowed for operations
   - Which operations (create, read, update, delete) are allowed

Example configuration:

```yaml
database:
  host: localhost
  port: 5432
  dbname: postgres
  user: postgres
  password: postgres
  
tables:
  - name: users
    allowed_columns:
      - id
      - name
      - email
      - created_at
    allowed_operations:
      - create
      - read
      - update
      - delete
  
  - name: products
    allowed_columns:
      - id
      - name
      - price
      - description
      - category
    allowed_operations:
      - create
      - read
      - update
      - delete
```

## Usage

Run the MCP server:

```
python postgresql_mcp_server.py
```

The server will start in stdio mode, ready to receive commands from an MCP client.

## Available MCP Tools

### list_tables

Lists all tables available in the configuration.

```python
response = list_tables()
```

### create_record

Creates a new record in the specified table.

```python
response = create_record(
    table_name="users",
    data={
        "name": "John Doe",
        "email": "john@example.com"
    }
)
```

### read_records

Reads records from the specified table with optional filtering.

```python
response = read_records(
    table_name="users",
    filters={"name": "John Doe"},
    limit=10,
    offset=0
)
```

### update_record

Updates a record in the specified table.

```python
response = update_record(
    table_name="users",
    record_id=1,
    data={"email": "newemail@example.com"},
    id_column="id"
)
```

### delete_record

Deletes a record from the specified table.

```python
response = delete_record(
    table_name="users",
    record_id=1,
    id_column="id"
)
```

### execute_query

Executes a custom SQL query.

```python
response = execute_query(
    query="SELECT * FROM users WHERE age > %s",
    params=[18]
)
```

### get_table_schema

Gets the schema information for a specific table.

```python
response = get_table_schema(table_name="users")
```

## Response Format

All tools return responses in a standard format:

```json
{
  "status": "success",
  "message": "Optional message",
  "records": [...],  // For read operations
  "record": {...},   // For create/update operations
  "count": 10        // For read operations
}
```

Or in case of an error:

```json
{
  "status": "error",
  "message": "Error message"
}
```

## Security Considerations

- The `execute_query` tool allows arbitrary SQL execution, which could be a security risk. Consider restricting its use or implementing additional validation.
- Database credentials are stored in plain text in the config.yaml file. Consider using environment variables or a secure secret management solution in production.
- The server validates table and column access based on the configuration, but it's important to ensure that the configuration itself is secure.

## License

[MIT License](LICENSE)
