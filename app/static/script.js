// Le pagine di accesso, registrazione e reset password hanno ognuna il proprio
// script (in fondo al template). Qui c'erano le versioni vecchie degli stessi
// gestori, con i messaggi in inglese: restando agganciate allo stesso form
// mandavano OGNI richiesta due volte. Nel reset password la seconda arrivava
// quando il codice era già stato consumato, quindi la password veniva
// cambiata ma l'utente vedeva "An error occurred. Please try again.".
//
// Se serve di nuovo codice condiviso fra le pagine pubbliche, va messo qui,
// ma senza duplicare gestori di form già presenti nei template.
console.log('Ispiramy frontend loaded');
