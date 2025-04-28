#!/usr/bin/env python3
"""
PostgreSQL MCP Server

This script creates an MCP server that provides CRUD operations
for specified tables in a PostgreSQL database.
"""

import os
import yaml
import json
import psycopg2
import psycopg2.extras
from fastmcp import FastMCP
from typing import Dict, List, Any, Optional, Union

# Initialize the MCP server
mcp = FastMCP(name="PostgreSQLServer")

# Load configuration
def load_config():
    """Load configuration from YAML file."""
    config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)

config = load_config()

# Database connection
def get_db_connection():
    """Create and return a database connection."""
    db_config = config['database']
    conn = psycopg2.connect(
        host=db_config['host'],
        port=db_config['port'],
        dbname=db_config['dbname'],
        user=db_config['user'],
        password=db_config['password']
    )
    conn.autocommit = True
    return conn

# Helper function to validate table and column access
def validate_table_access(table_name: str, operation: str, columns: Optional[List[str]] = None) -> bool:
    """
    Validate if the requested table, operation, and columns are allowed.
    
    Args:
        table_name: Name of the table to validate
        operation: Operation to validate (create, read, update, delete)
        columns: Optional list of columns to validate
        
    Returns:
        bool: True if access is allowed, False otherwise
    """
    # Check if table exists in config
    table_config = None
    for table in config.get('tables', []):
        if table['name'] == table_name:
            table_config = table
            break
    
    if not table_config:
        return False
    
    # Check if operation is allowed
    allowed_operations = table_config.get('allowed_operations', ['create', 'read', 'update', 'delete'])
    if operation not in allowed_operations:
        return False
    
    # Check if columns are allowed (if specified)
    if columns and 'allowed_columns' in table_config:
        allowed_columns = table_config['allowed_columns']
        for col in columns:
            if col not in allowed_columns:
                return False
    
    return True

# CRUD Operations as MCP tools

@mcp.tool()
def list_tables() -> Dict[str, Any]:
    """
    List all tables available in the configuration.
    
    Returns:
        Dict containing the list of tables and their allowed operations
    """
    tables_info = []
    for table in config.get('tables', []):
        tables_info.append({
            'name': table['name'],
            'allowed_operations': table.get('allowed_operations', ['create', 'read', 'update', 'delete']),
            'allowed_columns': table.get('allowed_columns', [])
        })
    
    return {
        'status': 'success',
        'tables': tables_info
    }

@mcp.tool()
def create_record(table_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new record in the specified table.
    
    Args:
        table_name: Name of the table to insert into
        data: Dictionary of column names and values
        
    Returns:
        Dict containing status and created record ID
    """
    # Validate table access
    columns = list(data.keys())
    if not validate_table_access(table_name, 'create', columns):
        return {
            'status': 'error',
            'message': f"Access denied for creating record in table '{table_name}' with the specified columns"
        }
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Build the SQL query
        columns_str = ', '.join(columns)
        placeholders = ', '.join(['%s'] * len(columns))
        values = [data[col] for col in columns]
        
        query = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders}) RETURNING *"
        
        cursor.execute(query, values)
        created_record = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return {
            'status': 'success',
            'message': f"Record created in table '{table_name}'",
            'record': dict(created_record)
        }
    
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }

@mcp.tool()
def read_records(table_name: str, filters: Optional[Dict[str, Any]] = None, 
                limit: Optional[int] = 100, offset: Optional[int] = 0) -> Dict[str, Any]:
    """
    Read records from the specified table.
    
    Args:
        table_name: Name of the table to read from
        filters: Optional dictionary of column names and values to filter by
        limit: Maximum number of records to return (default: 100)
        offset: Number of records to skip (default: 0)
        
    Returns:
        Dict containing status and records
    """
    # Validate table access
    if not validate_table_access(table_name, 'read'):
        return {
            'status': 'error',
            'message': f"Access denied for reading from table '{table_name}'"
        }
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Build the SQL query
        query = f"SELECT * FROM {table_name}"
        values = []
        
        # Add filters if provided
        if filters:
            filter_conditions = []
            for col, val in filters.items():
                if not validate_table_access(table_name, 'read', [col]):
                    return {
                        'status': 'error',
                        'message': f"Access denied for reading column '{col}' from table '{table_name}'"
                    }
                filter_conditions.append(f"{col} = %s")
                values.append(val)
            
            if filter_conditions:
                query += " WHERE " + " AND ".join(filter_conditions)
        
        # Add limit and offset
        query += f" LIMIT {limit} OFFSET {offset}"
        
        cursor.execute(query, values)
        records = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return {
            'status': 'success',
            'count': len(records),
            'records': [dict(record) for record in records]
        }
    
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }

@mcp.tool()
def update_record(table_name: str, record_id: Union[int, str], 
                 data: Dict[str, Any], id_column: str = 'id') -> Dict[str, Any]:
    """
    Update a record in the specified table.
    
    Args:
        table_name: Name of the table to update
        record_id: ID of the record to update
        Dictionary of column names and values to update
        id_column: Name of the ID column (default: 'id')
        
    Returns:
        Dict containing status and updated record
    """
    # Validate table access
    columns = list(data.keys())
    if not validate_table_access(table_name, 'update', columns + [id_column]):
        return {
            'status': 'error',
            'message': f"Access denied for updating record in table '{table_name}' with the specified columns"
        }
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Build the SQL query
        set_clauses = [f"{col} = %s" for col in columns]
        values = [data[col] for col in columns]
        values.append(record_id)  # For the WHERE clause
        
        query = f"UPDATE {table_name} SET {', '.join(set_clauses)} WHERE {id_column} = %s RETURNING *"
        
        cursor.execute(query, values)
        updated_record = cursor.fetchone()
        
        if not updated_record:
            return {
                'status': 'error',
                'message': f"Record with {id_column}={record_id} not found in table '{table_name}'"
            }
        
        cursor.close()
        conn.close()
        
        return {
            'status': 'success',
            'message': f"Record updated in table '{table_name}'",
            'record': dict(updated_record)
        }
    
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }

@mcp.tool()
def delete_record(table_name: str, record_id: Union[int, str], 
                 id_column: str = 'id') -> Dict[str, Any]:
    """
    Delete a record from the specified table.
    
    Args:
        table_name: Name of the table to delete from
        record_id: ID of the record to delete
        id_column: Name of the ID column (default: 'id')
        
    Returns:
        Dict containing status and message
    """
    # Validate table access
    if not validate_table_access(table_name, 'delete', [id_column]):
        return {
            'status': 'error',
            'message': f"Access denied for deleting from table '{table_name}'"
        }
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Build the SQL query
        query = f"DELETE FROM {table_name} WHERE {id_column} = %s RETURNING {id_column}"
        
        cursor.execute(query, [record_id])
        deleted_record = cursor.fetchone()
        
        if not deleted_record:
            return {
                'status': 'error',
                'message': f"Record with {id_column}={record_id} not found in table '{table_name}'"
            }
        
        cursor.close()
        conn.close()
        
        return {
            'status': 'success',
            'message': f"Record with {id_column}={record_id} deleted from table '{table_name}'"
        }
    
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }

@mcp.tool()
def execute_query(query: str, params: Optional[List[Any]] = None) -> Dict[str, Any]:
    """
    Execute a custom SQL query.
    WARNING: This tool should be used with caution as it allows arbitrary SQL execution.
    
    Args:
        query: SQL query to execute
        params: Optional list of parameters for the query
        
    Returns:
        Dict containing status and results (if applicable)
    """
    # This is a potentially dangerous operation, so you might want to restrict it
    # or implement additional validation
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cursor.execute(query, params or [])
        
        # Check if the query returns results
        try:
            records = cursor.fetchall()
            result = {
                'status': 'success',
                'count': len(records),
                'records': [dict(record) for record in records]
            }
        except psycopg2.ProgrammingError:
            # No results to fetch (e.g., for INSERT, UPDATE, DELETE)
            result = {
                'status': 'success',
                'message': f"Query executed successfully. {cursor.rowcount} rows affected."
            }
        
        cursor.close()
        conn.close()
        
        return result
    
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }

@mcp.tool()
def get_table_schema(table_name: str) -> Dict[str, Any]:
    """
    Get the schema information for a specific table.
    
    Args:
        table_name: Name of the table to get schema for
        
    Returns:
        Dict containing status and schema information
    """
    # Validate table access
    if not validate_table_access(table_name, 'read'):
        return {
            'status': 'error',
            'message': f"Access denied for reading schema of table '{table_name}'"
        }
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Query to get column information
        query = """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = %s
        ORDER BY ordinal_position
        """
        
        cursor.execute(query, [table_name])
        columns = cursor.fetchall()
        
        # Query to get primary key information
        query = """
        SELECT a.attname as column_name
        FROM pg_index i
        JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
        WHERE i.indrelid = %s::regclass AND i.indisprimary
        """
        
        cursor.execute(query, [table_name])
        primary_keys = [row['column_name'] for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return {
            'status': 'success',
            'table_name': table_name,
            'columns': [dict(col) for col in columns],
            'primary_keys': primary_keys
        }
    
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }

if __name__ == "__main__":
    # Run the MCP server in stdio mode
    mcp.run(transport="stdio")
