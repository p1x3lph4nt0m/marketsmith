# core/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.db import transaction
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.db.models import Count
from .models import GameSession, Player, Order, Transaction
from channels.layers import get_channel_layer
from django.views.decorators.csrf import csrf_exempt
from asgiref.sync import async_to_sync
from django.shortcuts import get_object_or_404, redirect
from core.models import Profile
import pandas as pd
from django.contrib.auth.models import User
from django.conf import settings

@csrf_exempt
def cron_ping(request):
    return HttpResponse({"status": "ok"})

@login_required
def cleanup_game(request, game_id):
    game = GameSession.objects.filter(id=game_id).first()

    if not game:
        return redirect("home")

    if game.is_finished:
        game.delete()

    return redirect("home")



def home(request):
    """
    Home / Lobby.
    If user is already assigned to a game, force redirect.
    """

    # 🚫 If not logged in → just show lobby
    if not request.user.is_authenticated:
        return render(request, 'lobby/lobby.html', {
            'assigned': False
        })

    # ✅ Logged-in logic
    existing_player = Player.objects.filter(
        user=request.user,
        game__is_active=False,
        game__is_finished=False
    ).first()

    if existing_player:
        return redirect('waiting_room', game_id=existing_player.game.id)

    if existing_player:
        return redirect('game_interface', game_id=existing_player.game.id)

    existing_player = Player.objects.filter(
        user=request.user,
        game__is_active=False
    ).first()

    if existing_player:
        return redirect('waiting_room', game_id=existing_player.game.id)

    profile = Profile.objects.filter(user=request.user).first()

    total_pnl = profile.total_pnl if profile else 0

    leaderboard = Profile.objects.values('user__username', 'total_pnl').order_by('-total_pnl')[:50]

    return render(request, "lobby/lobby.html",{
        "total_pnl": total_pnl,
        "leaderboard": leaderboard  # 2. Pass it to the template
    })


# ============================================================
# === VIEW: MATCHMAKING ENTRY POINT (CORE LOGIC) ==============
# ============================================================

@login_required
@require_POST
@transaction.atomic
def matchmaking(request):
    """
    MATCHMAKING RULES
    1. Rejoin unfinished game (waiting or active)
    2. Else join open waiting game (<6 players)
    3. Else create new game
    """

    # 1️⃣ Rejoin unfinished game
    existing_player = Player.objects.select_for_update().filter(
        user=request.user,
        game__is_finished=False
    ).first()

    if existing_player:
        game = existing_player.game
        if game.is_active:
            return redirect('game_interface', game_id=game.id)
        return redirect('waiting_room', game_id=game.id)

    # 2️⃣ Find open waiting game with space
    open_game = (
        GameSession.objects
        .select_for_update()
        .filter(is_active=False, is_finished=False)
        .annotate(player_count=Count('players'))
        .filter(player_count__lt=6)
        .order_by('created_at')
        .first()
    )

    # 3️⃣ Create game if none available
    if not open_game:
        open_game = GameSession.objects.create(
            room_code=f"G{GameSession.objects.count() + 1}"
        )

    # 4️⃣ Prevent duplicate join (safety)
    if Player.objects.filter(user=request.user, game=open_game).exists():
        return redirect('waiting_room', game_id=open_game.id)

    # 5️⃣ Assign seat
    seat_number = open_game.players.count() + 1

    Player.objects.create(
        user=request.user,
        game=open_game,
        seat_number=seat_number,
        cash=0,
        asset_count=2
    )

    # 6️⃣ BROADCAST UPDATED PLAYER COUNT
    player_count = open_game.players.count()

    async_to_sync(get_channel_layer().group_send)(
        f"waiting_{open_game.id}",
        {
            "type": "player_joined",
            "player_count": player_count
        }
    )

    # 7️⃣ Start game if full
    if player_count == 6:
        open_game.initialize_game()
        open_game.is_active = True
        open_game.save()
        # NOTIFY ALL WAITING CLIENTS THAT GAME STARTED
        async_to_sync(get_channel_layer().group_send)(
            f"waiting_{open_game.id}",
            {
                "type": "game_started",
            }
        )
        return redirect('game_interface', game_id=open_game.id)

    # 8️⃣ Otherwise stay in waiting room
    return redirect('waiting_room', game_id=open_game.id)





# ============================================================
# === VIEW: WAITING ROOM =====================================
# ============================================================

@login_required
def waiting_room(request, game_id):
    game = get_object_or_404(GameSession, id=game_id)

    player = Player.objects.filter(user=request.user, game=game).first()

    if not player:
        return redirect('home')


    if game.is_active:
        return redirect('game_interface', game_id=game.id)

    return render(request, 'lobby/waiting.html', {
        'game': game,
        'player': player,
        'player_count': game.players.count(),
        'max_players': 6,
    })



# ============================================================
# === VIEW: GAME INTERFACE ===================================
# ============================================================

@login_required
def game_interface(request, game_id):
    game = GameSession.objects.filter(id=game_id).first()
    if not game:
        return redirect("home")

    # =====================================================
    # === HANDLE FINISHED GAME (Leaderboard Phase) ========
    # =====================================================
    if game.is_finished:

        if not game.finished_at:
            return redirect("home")

        elapsed = (timezone.now() - game.finished_at).total_seconds()

        # After 30 seconds → go home
        if elapsed >= 30:
            return redirect("home")

        true_asset_value = sum(game.hidden_array) if game.hidden_array else 0

        players = []
        for p in game.players.select_related('user'):
            final_score = p.cash + ((p.asset_count-3) * true_asset_value)

            players.append({
                "username": p.user.username,
                "seat": p.seat_number,
                "cash": p.cash,
                "assets": p.asset_count,
                "net_pnl": final_score
            })

        players = sorted(players, key=lambda x: x["net_pnl"], reverse=True)

        return render(request, "core/game_over.html", {
            "game": game,
            "players": players,
            "remaining_time": int(30 - elapsed)
        })

    # =====================================================
    # === NORMAL GAME FLOW ================================
    # =====================================================

    player = Player.objects.filter(user=request.user, game=game).first()
    if not player:
        return redirect("home")

    trade_log = None

    # =====================================================
    # ================= FINAL PHASE =======================
    # =====================================================
    if game.current_round > 6:

        true_asset_value = sum(game.hidden_array) if game.hidden_array else 0

        # Mark game finished ONLY ONCE
        if not game.is_finished:
            for p in game.players.all():
                # Subtracts the 3 initial assets so doing nothing equals 0
                final_score = p.cash + ((p.asset_count - 3) * true_asset_value)

                profile, _ = Profile.objects.get_or_create(user=p.user)
                profile.total_pnl += final_score
                profile.save()

            game.is_finished = True
            game.is_active = False
            game.finished_at = timezone.now()
            game.save()

        # Redirect so top block handles leaderboard
        return redirect("game_interface", game_id=game.id)

    # =====================================================
    # ================= LOG PHASE =========================
    # =====================================================
    if game.round_phase == "log":

        elapsed = (timezone.now() - game.round_start_time).total_seconds()

        # 🔴 Move to next round after 10 seconds
        if elapsed >= 10:
            game.current_round += 1
            game.round_phase = "play"
            game.round_start_time = timezone.now()

            # 🔴 Clear previous trade log
            # game.last_trade_log = []                  // ADDED
            game.save()

            return redirect("game_interface", game_id=game.id)

        # 🔴 Fetch trade log from JSONField
        # trade_log = game.last_trade_log 
        trade_log = game.last_trade_log or []       # ADDED

        players = game.players.select_related('user').order_by('seat_number')

        return render(request, 'core/game.html', {
            'game': game,
            'player': player,
            'players': players,
            'question': None,
            'round_start_time': None,
            'current_server_time': timezone.now(),
            'round_end_time': 0,
            'show_trade_log_popup': True,
            'trade_log': trade_log,
        })

    # =====================================================
    # ================= PLAY PHASE ========================
    # =====================================================
    if game.round_phase == "play":

        if game.round_start_time is None:
            game.round_start_time = timezone.now()
            game.save()

        if game.current_round >= 4:
            for p in game.players.filter(has_received_bonus=False):
                p.asset_count += 1
                p.has_received_bonus = True
                p.save()

        elapsed = (timezone.now() - game.round_start_time).total_seconds()

        if elapsed >= 30:

            orders_qs = Order.objects.filter(
                game=game,
                round_number=game.current_round,
                is_active=True
            )

            orders_list = list(orders_qs.select_related('player'))

            orders_data = [
                {
                    'ID': o.player.id,
                    'Quote': o.order_type.lower(),
                    'Amt': o.price,
                    'Time': o.created_at.timestamp(),
                }
                for o in orders_list
            ]

            round_trades = []  # 🔴 This will go into last_trade_log
            full_trade_history = game.last_trade_log or []          # ADDED

            if orders_data:
                df = pd.DataFrame(orders_data)
                from .trade_execute import trades_df
                trades = trades_df(df)

                if not trades.empty:
                    for _, trade in trades.iterrows():
                        buyer = Player.objects.get(id=trade['from_id'])
                        seller = Player.objects.get(id=trade['to_id'])

                        ask_order = next(
                            (o for o in orders_list
                             if o.player.id == seller.id and o.order_type == 'ASK'),
                            None
                        )

                        if ask_order:
                            price = ask_order.price

                            # Update balances
                            buyer.cash -= price
                            buyer.asset_count += 1
                            seller.cash += price
                            seller.asset_count -= 1

                            buyer.save()
                            seller.save()

                            # 🔴 STORE TRADE IN JSON FIELD
                            round_trades.append({
                                "round": game.current_round,        # ADDED
                                "buyer": buyer.user.username,
                                "seller": seller.user.username,
                                "price": price
                            })

            # 🔴 Save trade log to GameSession
            full_trade_history.extend(round_trades)         # ADDED
            game.last_trade_log = full_trade_history
            orders_qs.update(is_active=False)

            game.round_phase = "log"
            game.round_start_time = timezone.now()
            game.save()

            return redirect("game_interface", game_id=game.id)

        index = game.current_round - 1
        question = (
            game.ques_list[index]
            if index < len(game.ques_list)
            else {"text": "Waiting..."}
        )

        players = game.players.select_related('user').order_by('seat_number')

        return render(request, 'core/game.html', {
            'game': game,
            'player': player,
            'players': players,
            'question': question,
            'round_start_time': game.round_start_time,
            'current_server_time': timezone.now(),
            'round_end_time': 30,
            'show_trade_log_popup': False,
            # 'trade_log': trade_log,
            'trade_log': game.last_trade_log or [],     # ADDED
        })




# ============================================================
# === API: PLACE ORDER (UNCHANGED CORE LOGIC) ================
# ============================================================

# ============================================================
# --- IT IS WRONG CURRENTLY A PLACEHOLDER----
# ============================================================

@login_required
@transaction.atomic
def api_place_order(request):
    if request.method != "POST":
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

    game_id = request.POST.get('game_id')
    order_type = request.POST.get('type')

    try:
        price = int(request.POST.get('price'))
    except (ValueError, TypeError):
        return JsonResponse({'status': 'error', 'message': 'Price must be a whole number'})

    game = GameSession.objects.select_for_update().get(id=game_id)
    player = Player.objects.select_for_update().get(user=request.user, game=game)

    current_round = game.current_round

    # ✅ LIMIT: 1 order per type per round
    if Order.objects.filter(
        player=player,
        game=game,
        round_number=current_round,
        order_type=order_type,
        is_active=True
    ).exists():
        return JsonResponse({
            'status': 'error',
            'message': f'Only ONE {order_type} allowed per round'
        })

    # ✅ SELL validation
    if order_type == 'ASK' and player.asset_count < 1:
        return JsonResponse({
            'status': 'error',
            'message': 'You have no assets to sell'
        })

    # ✅ Create order
    order = Order.objects.create(
        player=player,
        game=game,
        order_type=order_type,
        price=price,
        round_number=current_round,
        is_active=True
    )

    # --- Store order in DataFrame-compatible structure (in-memory, per game/round) ---
    # This is a placeholder: in production, use cache or DB for multi-process safety
    import threading
    if not hasattr(game, '_orders_df'):  # Attach to game instance for this process
        game._orders_df = []
        game._orders_df_lock = threading.Lock()
    with game._orders_df_lock:
        game._orders_df.append({
            'ID': player.id,
            'Quote': order_type.lower(),
            'Amt': price,
            'Time': order.created_at.timestamp(),
        })

    # ⛔ DO NOT deactivate other orders here

    return JsonResponse({
        'status': 'queued',
        'message': 'Order placed. Waiting for match.'
    })

def view_player_info(request):
    users = list(
        User.objects.all().values(
            "id",
            "username",
            "email",
            "is_active",
            "date_joined",
            "last_login"
        )
    )
    return JsonResponse({"users": users})
