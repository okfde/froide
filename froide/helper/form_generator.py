import re


class FormProcessor(object):
    CHECKBOX = re.compile(r"^(\s*)\[(\s*[xo]?\s*)\](.*)", re.MULTILINE)
    RADIOBOX = re.compile(r"^(\s*)\((\s*[xo]?\s*)\)(.*)", re.MULTILINE)
    radio_count = 0
    check_count = 0

    def run(self, lines):
        in_option = False
        in_form = False
        option_count = 1
        new_lines = []
        for i, line in enumerate(lines):
            was_form = True
            match_check = self.CHECKBOX.match(line)
            match_radio = self.RADIOBOX.match(line)
            if match_radio is not None:
                line = self.make_option(match_radio, option_count)
                if new_lines and not in_form:
                    new_lines[-1] = new_lines[-1][:-1]
                in_option = True
                in_form = True
            else:
                if in_option:
                    option_count += 1
                if match_check is not None:
                    line = self.make_check(match_check)
                    if new_lines and not in_form:
                        new_lines[-1] = new_lines[-1][:-1]
                    in_form = True
                else:
                    line = line + "\n"
                    was_form = False
                in_option = False
            if line is not None:
                if in_form:
                    if not line or (line and line[0] not in ".,;"):
                        if new_lines and new_lines[-1] and new_lines[-1][-1] not in "\n":
                            line = " " + line
                new_lines.append(line)
            if not was_form:
                in_form = False
        if new_lines:
            new_lines[-1] = new_lines[-1][:-1]
        return new_lines


class HtmlFormPreprocessor(FormProcessor):
    def make_option(self, match, count):
        self.radio_count += 1
        label = match.group(3).strip()
        checked = match.group(2).strip()
        if len(checked):
            checked = ' checked="checked"'
        return '''<label for="fg_option_%(radio)d"><input type="radio" id="fg_option_%(radio)d"%(checked)s" name="fg_radio_%(option)d" value="%(label)s"/> %(label)s</label>''' % {"radio": self.radio_count, "option": count, "label": label,
        "checked": checked}

    def make_check(self, match):
        self.check_count += 1
        label = match.group(3).strip()
        checked = match.group(2).strip()
        if len(checked):
            checked = ' checked="checked"'
        return '''<label for="fg_check_%(check)d"><input type="checkbox" id="fg_check_%(check)d"%(checked)s" name="fg_check_%(check)d" value="%(label)s"/> %(label)s</label>''' % {"check": self.check_count, "label": label,
        "checked": checked}


class TextFormPreprocessor(FormProcessor):
    def __init__(self, post_data):
        super(TextFormPreprocessor, self).__init__()
        self.post_data = post_data

    def make_option(self, match, count):
        self.radio_count += 1
        name = "fg_radio_%d" % count
        label = match.group(3).strip()
        if self.post_data.get(name, '') == label:
            return label.strip()
        return None

    def make_check(self, match):
        self.check_count += 1
        name = "fg_check_%d" % self.check_count
        label = match.group(3).strip()
        if self.post_data.get(name, ''):
            return label
        return None


class FormGenerator(object):
    def __init__(self, text, post=None):
        self.text = text
        self.post = post or {}

    def render_html(self):
        p = HtmlFormPreprocessor()
        return "".join(p.run(self.text.splitlines()))

    def render(self):
        p = TextFormPreprocessor(self.post)
        return "".join(p.run(self.text.splitlines()))


if __name__ == '__main__':
    s = '''I choose
    ( o ) ice cream
    (   ) waffles
with
    [ x ] chocolate sauce
    [ x ] caramel cream
    [   ] extra sugar
and I like it
    ( o ) baked
    (   ) cooked
.
Cheers!'''
    form = FormGenerator(s, {'fg_radio_1': 'ice cream', 'fg_check_3': 'yeah', 'fg_check_1': "on",
            "fg_radio_2": "baked"})
    print repr(form.render_html())
    print "-" * 30
    print form.render()
