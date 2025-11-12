from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from enum import Enum

class ImageLink(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    url: str
    name: str = Field(default="")
    description: str = Field(default="")

class Category(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    slug: str = Field(unique=True, index=True)
    icon: Optional[str] = Field(default="🎯")
    description: Optional[str] = Field(default=None)
    target: Optional[str] = Field(default=None)
    color: Optional[str] = Field(default="#4CAF50")

class User(SQLModel, table=True):
    """Modello utente/consulente"""
    __tablename__ = "user"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    password_md5: str
    nome: Optional[str] = None
    cognome: Optional[str] = None
    professione: Optional[str] = None
    
    # Relazione con categoria
    category_id: Optional[int] = Field(default=None, foreign_key="category.id")
    
    # Profilo consulente
    profile_picture: Optional[str] = None
    prezzo_consulenza: Optional[int] = None
    consulenze_vendute: int = Field(default=0)
    consulenze_acquistate: int = Field(default=0)
    bollini: int = Field(default=0)
    descrizione: Optional[str] = None
    aree_interesse: Optional[str] = None
    
    # Status
    confirmed: int = Field(default=0)
    confirmation_code: Optional[str] = None
    is_verified: bool = Field(default=False)
    is_anonymous: bool = Field(default=False)  # Se True, mostra "Utente #ID" invece del nome
    user_type_id: int = Field(default=1)  # 1=Utente, 2=Verificatore, 3=Amministratore
    
    # Timestamps
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

class Consultation(SQLModel, table=True):
    """Prenotazione consulenza"""
    __tablename__ = "consultation"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    consultant_id: int = Field(foreign_key="user.id")
    status: str = Field(default="pending")
    scheduled_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

# ========== MESSAGGISTICA MODELS ==========

class Conversation(SQLModel, table=True):
    """Conversazioni tra utenti (normalizzate: user1_id < user2_id)"""
    __tablename__ = "conversations"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user1_id: int = Field(foreign_key="user.id", index=True)
    user2_id: int = Field(foreign_key="user.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # ✅ Relationship con Message
    messages: List["Message"] = Relationship(back_populates="conversation")

class Message(SQLModel, table=True):
    """Messaggi nelle conversazioni"""
    __tablename__ = "messages"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    conversation_id: int = Field(foreign_key="conversations.id", index=True)
    sender_id: int = Field(foreign_key="user.id", index=True)
    content: str = Field(max_length=2000)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_read: bool = Field(default=False)
    
    # System messages and consultation offers
    is_system_message: bool = Field(default=False)
    consultation_offer_id: Optional[int] = Field(default=None, foreign_key="consultation_offers.id")
    
    # ✅ Relationship con Conversation
    conversation: Optional[Conversation] = Relationship(back_populates="messages")

# ========== COMMUNITY Q&A MODELS ==========

class QuestionStatus(str, Enum):
    """Status delle domande nella community"""
    OPEN = "open"
    ANSWERED = "answered"
    CLOSED = "closed"

class CommunityQuestion(SQLModel, table=True):
    """Domande nella community Q&A - solo domande con upvotes (like), senza risposte"""
    __tablename__ = "community_questions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    category_id: Optional[int] = Field(default=None, foreign_key="category.id")
    title: str = Field(max_length=200)
    description: str = Field(max_length=5000)
    status: str = Field(default=QuestionStatus.OPEN)
    views: int = Field(default=0)  # Ora rappresenta quanti utenti UNICI hanno cliccato "Messaggia"
    upvotes: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CommunityLike(SQLModel, table=True):
    """Like degli utenti sulle domande della community - un utente può mettere un solo like per domanda"""
    __tablename__ = "community_likes"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    question_id: int = Field(foreign_key="community_questions.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        # Constraint univoco: un utente può mettere un solo like per domanda
        table_args = (
            {'sqlite_autoincrement': True},
        )


class CommunityContact(SQLModel, table=True):
    """Traccia quali utenti hanno contattato (cliccato Messaggia) l'autore di una domanda"""
    __tablename__ = "community_contacts"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    question_id: int = Field(foreign_key="community_questions.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)  # Chi ha cliccato Messaggia
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        # Constraint univoco: un utente può incrementare il contatore una sola volta
        table_args = (
            {'sqlite_autoincrement': True},
        )


# ========== AVAILABILITY SYSTEM ==========

class AvailabilityBlock(SQLModel, table=True):
    """Blocchi di disponibilità per consulenze"""
    __tablename__ = "availability_block"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    date: datetime = Field(index=True)  # Data del giorno
    start_time: str  # Formato "HH:MM" es: "09:00"
    end_time: str    # Formato "HH:MM" es: "10:30"
    total_minutes: int  # Durata in minuti
    booked_minutes: int = Field(default=0)  # Minuti già prenotati
    status: str = Field(default="available")  # available, booked, unavailable
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Booking(SQLModel, table=True):
    """Prenotazioni di consulenze tra clienti e consulenti"""
    __tablename__ = "booking"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    client_user_id: int = Field(foreign_key="user.id", index=True)
    consultant_user_id: int = Field(foreign_key="user.id", index=True)
    availability_block_id: Optional[int] = Field(default=None, foreign_key="availability_block.id")
    
    booking_date: datetime = Field(index=True)
    start_time: str  # Formato "HH:MM"
    end_time: str    # Formato "HH:MM"
    duration_minutes: int  # 30, 60, 90, 120
    
    status: str = Field(default="pending")  # pending, confirmed, completed, cancelled, no_show
    price: Optional[Decimal] = None
    payment_status: str = Field(default="pending")  # pending, paid, refunded, failed
    payment_method: Optional[str] = None
    transaction_id: Optional[str] = None
    
    # Stripe payment fields
    stripe_checkout_session_id: Optional[str] = None  # Stripe Checkout Session ID
    stripe_payment_intent_id: Optional[str] = None  # Stripe Payment Intent ID
    
    meeting_link: Optional[str] = None  # Link Zoom/Google Meet
    client_notes: Optional[str] = None
    consultant_notes: Optional[str] = None
    
    # Join tracking - quando client/consultant cliccano "Partecipa"
    client_joined_at: Optional[datetime] = None
    consultant_joined_at: Optional[datetime] = None
    
    # Recording tracking - registrazione video call
    recording_sid: Optional[str] = None  # Agora Cloud Recording SID
    recording_resource_id: Optional[str] = None  # Agora resource ID
    recording_status: str = Field(default="not_started")  # not_started, recording, processing, completed, failed
    recording_url: Optional[str] = None  # S3 URL del video
    recording_duration: Optional[int] = None  # Durata in secondi
    recording_file_size: Optional[int] = None  # Dimensione file in bytes
    recording_started_at: Optional[datetime] = None
    recording_completed_at: Optional[datetime] = None
    
    cancellation_reason: Optional[str] = None
    cancelled_by: Optional[int] = Field(default=None, foreign_key="user.id")
    cancelled_at: Optional[datetime] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ConsultationOffer(SQLModel, table=True):
    __tablename__ = "consultation_offers"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    consultant_user_id: int = Field(foreign_key="user.id")
    client_user_id: int = Field(foreign_key="user.id")
    
    price: float = Field(gt=0)
    duration_minutes: int = Field(gt=0)
    
    status: str = Field(default="pending")  # pending, accepted, rejected, expired, completed
    booking_id: Optional[int] = Field(default=None, foreign_key="booking.id")
    
    message: Optional[str] = None
    expires_at: datetime
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Notification(SQLModel, table=True):
    """Modello per le notifiche utente"""
    __tablename__ = "notifications"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")  # Destinatario della notifica
    
    type: str  # 'booking', 'message', 'payment', 'cancellation', 'offer', etc.
    title: str  # Titolo breve della notifica
    message: str  # Messaggio completo
    
    # Riferimenti opzionali
    related_booking_id: Optional[int] = Field(default=None, foreign_key="booking.id")
    related_user_id: Optional[int] = Field(default=None, foreign_key="user.id")  # Chi ha generato la notifica
    
    # Link di azione
    action_url: Optional[str] = None  # URL dove andare cliccando la notifica
    
    is_read: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class NotificationType(SQLModel, table=True):
    """
    Configurazione tipi di notifica con flag per in-app e email.
    
    Permette di configurare quali notifiche inviare e come:
    - in_app: Mostra la notifica nel dropdown campanella
    - send_email: Invia anche email all'utente
    - email_subject: Oggetto dell'email
    - email_template: Nome del template HTML da usare
    """
    __tablename__ = "notification_types"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    type_key: str = Field(unique=True, index=True)  # es: 'booking_confirmed', 'reminder_1h', 'reminder_10min'
    name: str  # Nome descrittivo in italiano
    description: Optional[str] = None
    
    # Flags configurazione
    in_app: bool = Field(default=True)  # Mostra notifica in-app
    send_email: bool = Field(default=False)  # Invia anche email
    
    # Configurazione email
    email_subject: Optional[str] = None  # Oggetto email (può contenere {variables})
    email_template: Optional[str] = None  # Nome template HTML (es: 'booking_confirmation.html')
    
    # Metadata
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
