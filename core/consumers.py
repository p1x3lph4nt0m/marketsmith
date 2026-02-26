# core/consumers.py
from channels.generic.websocket import AsyncWebsocketConsumer
import json

class WaitingConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.game_id = self.scope["url_route"]["kwargs"]["game_id"]
        self.group_name = f"waiting_{self.game_id}"

        # JOIN GROUP (THIS WAS MISSING)
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def player_joined(self, event):
        await self.send(text_data=json.dumps({
            "type": "player_joined",
            "player_count": event["player_count"]
        }))

    async def game_started(self, event):
        await self.send(text_data=json.dumps({
            "type": "game_started"
        }))


