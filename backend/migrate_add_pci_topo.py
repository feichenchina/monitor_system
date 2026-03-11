from sqlmodel import Session, create_engine, text
import os

# Try to locate the database file
db_name = "database.db"
if os.path.exists(db_name) and os.path.getsize(db_name) > 0:
    sqlite_file_name = db_name
elif os.path.exists(f"../{db_name}") and os.path.getsize(f"../{db_name}") > 0:
    sqlite_file_name = f"../{db_name}"
else:
    # Default fallback
    sqlite_file_name = db_name

print(f"Using database: {os.path.abspath(sqlite_file_name)}")
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(sqlite_url)

def migrate():
    with Session(engine) as session:
        try:
            # pci_topo_json is Optional[str], which maps to TEXT in SQLite
            session.exec(text("ALTER TABLE machine ADD COLUMN pci_topo_json TEXT"))
            print("Added column pci_topo_json")
        except Exception as e:
            print(f"Column pci_topo_json might already exist: {e}")
            
        session.commit()

if __name__ == "__main__":
    migrate()
