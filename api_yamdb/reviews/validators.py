from django.forms import ValidationError
from django.utils.timezone import now


def validate_title_year(value):
    if 1500 < value < 1500:
        raise ValidationError(
            'значение должно быть больше 1500 ',
            'и меньше текущего года'
        )