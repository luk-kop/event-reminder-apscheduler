from flask import flash
from wtforms.validators import ValidationError
from dns import resolver


def flash_errors(form):
    """
    Function flashes form errors.
    """
    for field, errors in form.errors.items():
        for error in errors:
            flash(f'The error in "{getattr(form, field).label.text}" field - "{error}"', 'danger')


class DateOrTimeChecker:
    """
    Custom class validator.
    Validates whether the date from designated field is earlier or later enough than the date in another field

    :param later_than:
        If True, check whether date from the field being checked is later than other_field date value
    :param earlier_than:
        If True, check whether date from the field being checked is earlier than other_field date value
    :param time_check:
        If True, check whether time from the field being checked is earlier than other_field time value
    :param message:
        Error message to raise in case of a validation error.
    """
    def __init__(self, other_field, later_than=False, earlier_than=False, time_check=False, message=None):
        if not later_than and not earlier_than:
            raise ValueError('Check data validator must have later_than or earlier_than properties enabled.')
        self.other_field = other_field
        self.message = message
        self.later_than = later_than
        self.earlier_than = earlier_than
        self.time_check = time_check

    def __call__(self, form, field):
        field_benchmark = form[self.other_field]
        data_benchmark = field_benchmark.data
        data_checked = field.data
        time_check = self.time_check
        # Exit validator only if not time check.
        if not time_check and (not data_checked or not data_benchmark):
            return
        if time_check and (data_checked or data_benchmark):
            if data_checked and not data_benchmark:
                message = field.gettext(f'The "{field_benchmark.label.text}" value should be specified')
                raise ValidationError(message)
            elif not data_checked and data_benchmark:
                message = field.gettext(f'The "{field.label.text}" value should be specified')
                raise ValidationError(message)
            # Exit if not the same day
            same_day = form['date_event_start'].data == form['date_event_stop'].data
            if not same_day:
                return
        if self.later_than and data_checked and data_benchmark:
            if data_checked < data_benchmark:
                message = self.message
                if message is None:
                    message = field.gettext(f'The value must be later or the same as "{field_benchmark.label.text}"')
                raise ValidationError(message)
        elif self.earlier_than and data_checked and data_benchmark:
            if data_checked > data_benchmark:
                message = self.message
                if message is None:
                    message = field.gettext(f'The value must be earlier or the same as "{field_benchmark.label.text}"')
                raise ValidationError(message)


class MxRecordValidator:
    """
    Custom class validator.
    Validates whether the e-mail domain or MX record exist.
    """
    def __init__(self, message=None):
        self.message = message

    def __call__(self, form, field):
        message = self.message
        email_address = field.data
        records = False
        # Pull domain name from email address
        domain_name = email_address.split('@')[1]
        try:
            # get MX record for the domain
            records = resolver.resolve(domain_name, 'MX')
        except resolver.NXDOMAIN:
            message = field.gettext(f'Please enter valid email address. The domain "{domain_name}" does not exist')
        except resolver.NoAnswer:
            message = field.gettext(f'Please enter valid email address. The domain "{domain_name}" has no e-mail service')
        except resolver.NoResolverConfiguration:
            message = field.gettext(f'Please check your network connection"')
        if not records:
            if message is None:
                message = field.gettext(f'Please enter valid email address')
            raise ValidationError(message)

