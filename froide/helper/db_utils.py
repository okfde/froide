from django.db import IntegrityError
from django.template.defaultfilters import slugify


def save_obj_with_slug(obj, attribute='title', **kwargs):
    obj.slug = slugify(getattr(obj, attribute))
    return save_obj_unique(obj, 'slug', **kwargs)


def save_obj_unique(obj, attr, count=0, postfix_format='-{count}'):
    klass = obj.__class__
    MAX_COUNT = 10000  # max 10 thousand loops
    base_attr = getattr(obj, attr)
    initial_count = count
    first_round = count == 0
    postfix = ''
    while True:
        try:
            while initial_count - count < MAX_COUNT:
                if not first_round:
                    postfix = postfix_format.format(count=count)
                if not klass.objects.filter(**{
                            attr: getattr(obj, attr) + postfix
                        }).exists():
                    break
                if first_round:
                    first_round = False
                    count = klass.objects.filter(**{
                        '%s__startswith' % attr: base_attr
                    }).count()
                else:
                    count += 1
            setattr(obj, attr, base_attr + postfix)
            obj.save()
        except IntegrityError:
            if count - initial_count < MAX_COUNT:
                first_round = False
                count = klass.objects.filter(**{
                    '%s__startswith' % attr: base_attr
                }).count()
            else:
                raise
        else:
            break
