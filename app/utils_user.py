def has_payment_method(user) -> bool:
    """Controlla se un consulente ha almeno un metodo di pagamento configurato (Stripe o PayPal)."""
    return bool(getattr(user, 'stripe_onboarding_complete', False)) or bool(getattr(user, 'paypal_email', None))

def get_display_name(user, include_full_name=True):
    """
    Restituisce il nome da visualizzare per un utente.
    Se is_anonymous=True, mostra "Utente #ID"
    Altrimenti mostra nome e cognome
    
    Args:
        user: Oggetto User
        include_full_name: Se False, mostra solo il nome (per contesti brevi)
    """
    if user.is_anonymous:
        return f"Utente #{user.id}"
    
    if include_full_name:
        return f"{user.nome or ''} {user.cognome or ''}".strip() or f"Utente #{user.id}"
    else:
        return user.nome or f"Utente #{user.id}"


def get_default_avatar(user):
    """
    Restituisce il path dell'avatar di default in base al genere dell'utente.
    - M → avatar-male.svg
    - F → avatar-female.svg
    - None/altro → avatar-default.svg
    """
    if hasattr(user, 'genere') and user.genere == 'M':
        return '/static/avatar-male.svg'
    elif hasattr(user, 'genere') and user.genere == 'F':
        return '/static/avatar-female.svg'
    return '/static/avatar-default.svg'
