import re


class FormProcessor(object):
    CHECKBOX = re.compile(r"^\s*\[(\s*[xo]?\s*)\](.*)")
    RADIOBOX = re.compile(r"^\s*\((\s*[xo]?\s*)\)(.*)")
    radio_count = 0
    check_count = 0

    def run(self, lines):
        in_option = False
        option_count = 1
        for i, line in enumerate(lines):
            match_check = self.CHECKBOX.match(line)
            match_radio = self.RADIOBOX.match(line)
            if match_radio is not None:
                in_option = True
                line = self.make_option(match_radio, option_count)
            else:
                if in_option:
                    option_count += 1
                in_option = False
                if match_check is not None:
                    line = self.make_check(match_check)
            if line is not None:
                yield line


class HtmlFormPreprocessor(FormProcessor):
    def make_option(self, match, count):
        self.radio_count += 1
        label = match.group(2).lstrip()
        checked = match.group(1).strip()
        if len(checked):
            checked = ' checked="checked"'
        return '''<label for="fg_option_%(radio)d">
    <input type="radio" id="fg_option_%(radio)d"%(checked)s" name="fg_radio_%(option)d" value="%(label)s"/>%(label)s
</label>''' % {"radio": self.radio_count, "option": count, "label": label,
            "checked": checked}

    def make_check(self, match):
        self.check_count += 1
        label = match.group(2).lstrip()
        checked = match.group(1).strip()
        if len(checked):
            checked = ' checked="checked"'
        return '''<label for="fg_check_%(check)d">
    <input type="checkbox" id="fg_check_%(check)d"%(checked)s" name="fg_check_%(check)d" value="%(label)s"/>%(label)s
</label>''' % {"check": self.check_count, "label": label,
            "checked": checked}

class TextFormPreprocessor(FormProcessor):
    def __init__(self, post_data):
        super(TextFormPreprocessor, self).__init__()
        self.post_data = post_data

    def make_option(self, match, count):
        self.radio_count += 1
        name = "fg_radio_%d" % count
        label = match.group(2).lstrip()
        if self.post_data.get(name, '') == label:
            return label.strip()
        return None

    def make_check(self, match):
        self.check_count += 1
        name = "fg_check_%d" % self.check_count
        label = match.group(2).lstrip()
        if self.post_data.get(name, ''):
            return label
        return None


class FormGenerator(object):
    def __init__(self, text, post=None):
        self.text = text
        self.post = post or {}

    def render_html(self):
        p = HtmlFormPreprocessor()
        return "\n".join(p.run(self.text.splitlines()))

    def render(self):
        p = TextFormPreprocessor(self.post)
        return "\n".join(p.run(self.text.splitlines()))


if __name__ == '__main__':
    s = '''This is a test form
    ( o ) Either this
    (   ) or that
But you also have both:
    [ x ] This
    [ x ] and that
    [   ] maybe not this one.
Some more options:
    ( o ) Either this
    (   ) or that

Cheers!'''
    form = FormGenerator(s)
    print form.render_html()
    print "-" * 30
    print form.render({'fg_radio_1': 'or that', 'fg_check_3': 'yeah',
            "fg_radio_2": "Either this"})



