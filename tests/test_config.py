from app.database import get_session
from app.utils_user import get_config_int

with get_session() as db:
    max_msgs = get_config_int(db, 'MAX_MESSAGES_PER_CONVERSATION', 80)
    max_len = get_config_int(db, 'MAX_MESSAGE_LENGTH', 1000)
    print(f'MAX_MESSAGES: {max_msgs}')
    print(f'MAX_LENGTH: {max_len}')
