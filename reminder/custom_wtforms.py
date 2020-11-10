from flask import flash

from wtforms.validators import ValidationError


def flash_errors(form):
    """
    Function flashes form errors.
    """
    for field, errors in form.errors.items():
        for error in errors:
            flash(f'The error in "{getattr(form, field).label.text}" field - "{error}"', 'danger')


class CheckDuplicate:
    """
    Custom class validator.
    Checks whether the data in the designated field already exists in db.
    """
    def __init__(self, model, table, case_sensitive=False, message=None):
        self.model = model
        self.table = table
        self.case_sensitive = case_sensitive
        self.message = message

    def __call__(self, form, field):
        if self.case_sensitive:
            exist = self.model.query.filter(self.table.like('%' + field.data + '%')).first()
        else:
            exist = self.model.query.filter(self.table.ilike('%' + field.data + '%')).first()
        if exist:
            message = self.message
            if message is None:
                message = field.gettext(f'Data from "{field.data}" already exists ind db.')
            raise ValidationError(message)