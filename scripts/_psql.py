#!/usr/bin/env python3
"""
Portable PostgreSQL query helper for shell scripts.
Usage: python scripts/_psql.py <DATABASE_URL> <query>
"""
import sys
import psycopg2
import os

def run_query(database_url, query):
    """Execute a SQL query and return results as TSV."""
    try:
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        cur.execute(query)
        
        # Fetch results if it's a SELECT
        if cur.description:
            # Print column names
            columns = [desc[0] for desc in cur.description]
            print("\t".join(columns))
            
            # Print rows
            for row in cur.fetchall():
                print("\t".join(str(val) if val is not None else "NULL" for val in row))
        else:
            # For non-SELECT queries
            conn.commit()
            print(f"Query executed successfully. Rows affected: {cur.rowcount}")
        
        cur.close()
        conn.close()
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scripts/_psql.py <DATABASE_URL> <query>", file=sys.stderr)
        sys.exit(1)
    
    database_url = sys.argv[1]
    query = sys.argv[2]
    
    sys.exit(run_query(database_url, query))
