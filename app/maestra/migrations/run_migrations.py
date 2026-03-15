"""Run Maestra-specific PG migrations."""
import os
import glob
import psycopg2


def run():
    url = os.environ.get("SUPABASE_DB_URL")
    if not url:
        raise RuntimeError(
            "SUPABASE_DB_URL not set. Cannot run Maestra migrations."
        )
    conn = psycopg2.connect(url)
    conn.autocommit = True
    cur = conn.cursor()
    migration_dir = os.path.join(os.path.dirname(__file__))
    for f in sorted(glob.glob(os.path.join(migration_dir, "*.sql"))):
        fname = os.path.basename(f)
        print(f"Running {fname}...")
        with open(f) as sql_file:
            cur.execute(sql_file.read())
        print(f"  Done.")
    cur.close()
    conn.close()
    print("All Maestra migrations complete.")


if __name__ == "__main__":
    run()
