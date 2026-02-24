from sqlmodel import Session, create_engine, text
import os

# Explicitly use the path C:\monitor-system\backend\database.db
# Based on previous ls, the backend folder is c:\monitor-system\backend
# And database.py says sqlite_file_name = "database.db", so it's relative to where the app runs.
# Usually main.py runs from C:\monitor-system, so database.db might be in C:\monitor-system\database.db OR C:\monitor-system\backend\database.db

# Let's check where the actual file is
base_dir = r"C:\monitor-system"
possible_locations = [
    os.path.join(base_dir, "database.db"),
    os.path.join(base_dir, "backend", "database.db")
]

db_path = None
for path in possible_locations:
    if os.path.exists(path):
        db_path = path
        break

if not db_path:
    # If not found, assume C:\monitor-system\backend\database.db as default for creation or it's just not there yet
    db_path = os.path.join(base_dir, "backend", "database.db")
    print(f"Database not found, defaulting to: {db_path}")

print(f"Using database: {db_path}")
sqlite_url = f"sqlite:///{db_path}"

engine = create_engine(sqlite_url)

def migrate():
    with Session(engine) as session:
        try:
            # Check if table exists
            session.exec(text("SELECT 1 FROM machine LIMIT 1"))
        except Exception as e:
            print(f"Error accessing machine table: {e}")
            return

        try:
            session.exec(text("ALTER TABLE machine ADD COLUMN is_own BOOLEAN DEFAULT 0"))
            print("Added column is_own")
        except Exception as e:
            print(f"Column is_own might already exist or error: {e}")
            
        session.commit()

if __name__ == "__main__":
    migrate()
