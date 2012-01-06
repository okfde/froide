import re
import htmlentitydefs

##
# From http://effbot.org/zone/re-sub.htm#unescape-html
# Removes HTML or XML character references and entities from a text string.
#
# @param text The HTML (or XML) source text.
# @return The plain text, as a Unicode string, if necessary.

def unescape(text):
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text # leave as is
    return re.sub("&#?\w+;", fixup, text)

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

def remove_signature(text, dividers=[re.compile(r'^--\s+')]):
    lines = []
    found = False
    for line in text.splitlines():
        for divider in dividers:
            if divider.match(line) is not None:
                found = True
                break
        if found:
            break
        lines.append(line)
    return u"\n".join(lines)

EMAIL_NAME_RE = re.compile(r'[,:]? "?.*?"? <[^@]+@[^>]+>')

def replace_email_name(text, replacement=u""):
    return EMAIL_NAME_RE.sub(replacement, text)

EMAIL_RE = re.compile(r'[^\s]+@[^\s]+')

def replace_email(text, replacement=u""):
    return EMAIL_RE.sub(replacement, text)
