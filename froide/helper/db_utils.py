from django.db import IntegrityError
from django.template.defaultfilters import slugify


def save_obj_with_slug(obj, attribute='title', count=0):
    klass = obj.__class__
    MAX_COUNT = 10000000  # max 10 million loops
    obj.slug = slugify(getattr(obj, attribute))
    first_round = count == 0
    postfix = ''
    while True:
        try:
            while count < MAX_COUNT:
                if not first_round:
                    postfix = '-%d' % count
                if not klass.objects.filter(
                        slug=obj.slug + postfix).exists():
                    break
                if first_round:
                    first_round = False
                    count = klass.objects.filter(
                            slug__startswith=obj.slug).count()
                else:
                    count += 1
            obj.slug += postfix
            obj.save()
        except IntegrityError:
            if count < MAX_COUNT:
                first_round = False
                count = klass.objects.filter(
                        slug__startswith=obj.slug).count()
            else:
                raise
        else:
            break
