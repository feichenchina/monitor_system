from sqlmodel import Session, create_engine, text

sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(sqlite_url)

def migrate():
    with Session(engine) as session:
        try:
            session.exec(text("ALTER TABLE machine ADD COLUMN ibmc_ip VARCHAR"))
            print("Added column ibmc_ip")
        except Exception as e:
            print(f"Column ibmc_ip might already exist: {e}")

        try:
            session.exec(text("ALTER TABLE machine ADD COLUMN ibmc_password VARCHAR"))
            print("Added column ibmc_password")
        except Exception as e:
            print(f"Column ibmc_password might already exist: {e}")
            
        session.commit()

if __name__ == "__main__":
    migrate()
