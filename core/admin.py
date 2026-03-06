from django.contrib import admin
from .models import GameSession, Player, Order, Transaction, Profile

admin.site.register(GameSession)
admin.site.register(Player)
admin.site.register(Order)
admin.site.register(Transaction)
admin.site.register(Profile)