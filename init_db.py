import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import os
from config.settings import DB_URL
from sqlalchemy import text, create_engine

def init_database():
    print("Initializing database schema...")
    
    schema_file = Path(__file__).parent / "database" / "schema.sql"
    if not schema_file.exists():
        print(f"Schema file not found: {schema_file}")
        return False
    
    with open(schema_file, 'r') as f:
        schema_sql = f.read()
    
    try:
        engine = create_engine(DB_URL)
        with engine.connect() as conn:
            for statement in schema_sql.split(';'):
                statement = statement.strip()
                if statement:
                    print(f"Executing: {statement[:80]}...")
                    conn.execute(text(statement))
            conn.commit()
        print("Schema created successfully")
        return True
    except Exception as e:
        print(f"Error creating schema: {e}")
        return False

def load_seed_data():
    """Load seed data from seed_data.sql"""
    print("\nLoading seed data...")
    
    # Read seed data
    seed_file = Path(__file__).parent / "database" / "seed_data.sql"
    if not seed_file.exists():
        print(f"Seed data file not found: {seed_file}")
        return False
    
    with open(seed_file, 'r') as f:
        seed_sql = f.read()
    
    try:
        engine = create_engine(DB_URL)
        with engine.connect() as conn:
            for statement in seed_sql.split(';'):
                statement = statement.strip()
                if statement and not statement.startswith('--'):  
                    print(f"Executing: {statement[:80]}...")
                    conn.execute(text(statement))
            conn.commit()
        print("Seed data loaded successfully")
        return True
    except Exception as e:
        print(f"Error loading seed data: {e}")
        return False

def verify_data():
    print("\nVerifying data...")
    try:
        from database.connection import get_session
        from database.models import MarketData, NewsSentiment, Anomaly, Forecast
        
        with get_session() as session:
            market_count = session.query(MarketData).count()
            sentiment_count = session.query(NewsSentiment).count()
            anomaly_count = session.query(Anomaly).count()
            forecast_count = session.query(Forecast).count()
            
            print(f"MarketData rows: {market_count}")
            print(f"NewsSentiment rows: {sentiment_count}")
            print(f"Anomaly rows: {anomaly_count}")
            print(f"Forecast rows: {forecast_count}")
            
            if market_count > 0:
                print("Data verification successful!")
                return True
            else:
                print("No data found - check seed_data.sql is being executed correctly")
                return False
    except Exception as e:
        print(f"Error verifying data: {e}")
        return False

if __name__ == "__main__":
    print(f"Database URL: {DB_URL}")
    print("=" * 60)
    
    success = init_database() and load_seed_data()
    
    if success:
        verify_data()
        print("\n" + "=" * 60)
        print("Database initialization complete!")
        print("You can now start the API and dashboard")
    else:
        print("\n" + "=" * 60)
        print("Database initialization failed!")
