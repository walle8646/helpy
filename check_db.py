from sqlmodel import create_engine, Session, text
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./helpy.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {}
if "sqlite" in DATABASE_URL:
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)

with Session(engine) as session:
    # Prova 1: text() con select *
    result = session.exec(text('SELECT property_value FROM configuration_property WHERE property_key = "MAX_MESSAGES_PER_CONVERSATION"')).first()
    print(f'\n--- Test Query ---')
    print(f'Result type: {type(result)}')
    print(f'Result value: {result}')
    if result:
        print(f'Result[0]: {result[0]}')
        print(f'Result as list: {list(result)}')
