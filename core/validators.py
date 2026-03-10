from django.core.exceptions import ValidationError


def validate_number_of_seats_greater_then_zero(instance, source):
    if source == "request":
        seats = instance.required_seats
    else:
        seats = instance.available_seats

    if not seats:
        raise ValidationError("The number of seats is mandatory")
    if seats <= 0:
        raise ValidationError("You cant create a ride with less that 1 seat available")
    

def validate_all_field_values_passed(self):
    pass