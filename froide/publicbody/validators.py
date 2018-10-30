import csv
import logging

from django import forms
from django.conf import settings

import requests
from pyisemail import is_email
try:
    import phonenumbers
except ImportError:
    phonenumbers = None


logger = logging.getLogger(__name__)


class PublicBodyValidator():
    def __init__(self, pbs):
        self.pbs = pbs

    def get_validation_results(self):
        self.is_valid = True

        for res in validate_publicbodies(self.pbs):
            self.is_valid = False
            yield res

    def write_csv(self, stream):
        writer = None
        for result in self.get_validation_results():
            if writer is None:
                fieldnames = list(result.keys())
                writer = csv.DictWriter(stream, fieldnames)
                writer.writeheader()
            writer.writerow(result)


def validate_publicbodies(queryset):
    validators = [
        (validate_email, 'email'),
        (validate_url, 'url'),
    ]
    if phonenumbers is not None:
        validators.append((validate_fax, 'fax',))

    for pb in queryset.iterator():
        result = run_validators(validators, pb)
        if not result['error']:
            continue
        result['id'] = pb.id
        result['name'] = pb.name
        yield result


def run_validators(validators, pb):
    results = {
        'error': False
    }
    for validator, attr in validators:
        val = getattr(pb, attr)
        results[attr] = None
        results[attr + '_error'] = False
        if not val:
            continue
        try:
            logger.debug('Validating %s of %s (%s)', attr, pb.name, pb.id)
            ret = validator(val)
        except forms.ValidationError as e:
            results[attr] = '\n'.join(e)
            results[attr + '_error'] = True
            results['error'] = True
        else:
            results[attr] = ret
    return results


def validate_email(email):
    diagnosis = is_email(email, diagnose=True, check_dns=True)
    if diagnosis.diagnosis_type != 'VALID':
        raise forms.ValidationError(
            diagnosis.diagnosis_type, code=diagnosis.code
        )


def validate_url(url):
    try:
        response = requests.get(url, timeout=10)
    except Exception as e:
        raise forms.ValidationError(str(e))
    if response.history:
        return response.url


def validate_fax(fax):
    try:
        number = phonenumbers.parse(fax, settings.LANGUAGE_CODE.upper())
    except phonenumbers.phonenumberutil.NumberParseException:
        raise forms.ValidationError('Fax number cannot be parsed')
    if not phonenumbers.is_possible_number(number):
        raise forms.ValidationError('Impossible fax number')
    if not phonenumbers.is_valid_number(number):
        raise forms.ValidationError('Invalid fax number')
