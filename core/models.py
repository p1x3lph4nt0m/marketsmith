# core/models.py
from django.contrib.auth.decorators import login_required
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
import random
from django.shortcuts import redirect, get_object_or_404

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    techhnex_id = models.CharField(max_length=100, unique=True, null=True, blank=True)

    total_pnl = models.IntegerField(default=0)

    def __str__(self):
        return self.user.username



# --- 1. The Game Table (The Environment) ---
class GameSession(models.Model):
    room_code = models.CharField(max_length=6, unique=True)
    is_active = models.BooleanField(default=False)  # game started
    is_finished = models.BooleanField(default=False)  # game ended
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    # The Hidden Array: We store [d1, d2, d3, d4, d5, d6] as a JSON list
    # Example: [5, 1, 9, 2, 8, 3] -> Sum = 28 (True Asset Value)
    hidden_array = models.JSONField(default=list, blank=True)
    ques_list = models.JSONField(default=list, blank=True)

    last_trade_log = models.JSONField(default=list, blank=True)
    current_round_trades = models.JSONField(default=list, blank=True)

    current_round = models.IntegerField(default=1)  # 1 to 6
    round_start_time = models.DateTimeField(null=True, blank=True)

    round_phase = models.CharField(max_length=20, default="play")
    # values:
    # play
    # log
    # final

    def initialize_game(self):
        from .question_generate import generate_question
        self.hidden_array = []
        self.ques_list = []
        self.current_round = 1
        self.is_active = True
        self.round_phase = "play"
        self.round_start_time = timezone.now()

        for _ in range(6):
            q = generate_question()
            self.hidden_array.append(q['answer'])
            self.ques_list.append(q['question'])

        self.save()


# --- 2. The User/Player (The Actor) ---
class Player(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    game = models.ForeignKey(GameSession, on_delete=models.CASCADE, related_name='players')

    # CHARACTERISTICS
    class Meta:
        unique_together = (
            ('game', 'seat_number'),
            ('user', 'game'),
        )

    seat_number = models.IntegerField()  # 1 to 6

    # CHANGED: Converted to IntegerField. Default is 0.
    # Negative values are allowed by default in IntegerField.
    cash = models.IntegerField(default=0)

    asset_count = models.IntegerField(default=2)  # Starts with 2 assets

    # For the extra 1 asset after 3 round
    has_received_bonus = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} (Seat {self.seat_number})"


# --- 3. The Market (The Logic) ---
# --- NEEDS TO BE VERIFIED CURRENTLY A PLACEHOLDER----
class Order(models.Model):
    ORDER_TYPES = (('BID', 'Buy'), ('ASK', 'Sell'))

    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    game = models.ForeignKey(GameSession, on_delete=models.CASCADE)

    order_type = models.CharField(max_length=3, choices=ORDER_TYPES)
    price = models.IntegerField()

    round_number = models.IntegerField()

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Transaction(models.Model):
    game = models.ForeignKey(GameSession, on_delete=models.CASCADE)
