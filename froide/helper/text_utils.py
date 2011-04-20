import re

def remove_quote(text, replacement=u"", quote_prefix=u">"):
    lines = []
    put_replacement = True
    for line in text.splitlines():
        if line.strip().startswith(quote_prefix):
            if put_replacement:
                lines.append(replacement)
                put_replacement = False
        else:
            lines.append(line)
            put_replacement = True
    return u"\n".join(lines)

SIGNATURE_DIVIDER = re.compile(r'(\-\- |[ \-_]+)')

def remove_signature(text, replacement=u""):
    lines = []
    for line in text.splitlines():
        if SIGNATURE_DIVIDER.match(line.strip()) is not None:
            break
        lines.append(line)
    return u"\n".join(lines)

EMAIL_NAME_RE = re.compile(r'[,:]? "?.*?"? <[^@]+@[^>]+>')

def replace_email_name(text, replacement=u""):
    return EMAIL_NAME_RE.sub(replacement, text)

EMAIL_RE = re.compile(r'[^\s]+@[^\s]+')

def replace_email(text, replacement=u""):
    return EMAIL_RE.sub(replacement, text)
