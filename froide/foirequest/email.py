import imaplib

def get_unread_mails(host, user, password):
    mail = imaplib.IMAP4_SSL(host, 993)
    mail.login(user, password)
    try:
        status, count = mail.select('Inbox')
        typ, data = mail.search(None, 'UNSEEN')
        for num in data[0].split():
            status, data = mail.fetch(num, '(RFC822)')
            yield data[0][1]
    finally:
        mail.close()
        mail.logout()

