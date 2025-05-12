from django import template

register = template.Library()

@register.filter
def stars(rating: int) -> str:
    return ('★' * rating) + ('☆' * (5 - rating))