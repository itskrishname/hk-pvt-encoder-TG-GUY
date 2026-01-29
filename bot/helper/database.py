from motor.motor_asyncio import AsyncIOMotorClient
from bot.config import Config

class Database:
    def __init__(self):
        self.client = AsyncIOMotorClient(
            Config.MONGO_URI,
            maxPoolSize=50,
            minPoolSize=5,
            serverSelectionTimeoutMS=5000
        )
        self.db = self.client[Config.DB_NAME]
        self.collection = self.db[Config.COLLECTION_NAME]
        try:
            self.client.admin.command('ping')
            print("MongoDB connection successful")
        except Exception as e:
            print(f"MongoDB connection failed: {e}")
    
    defaults = {
        "crf": 29,
        "preset": "ultrafast",
        "resolution": "640x360",
        "audio_b": "32k",
        "audio_codec": "aac",
        "video_codec": "libx265",
        "video_bitrate": 0,
        "bits": "8",
        "watermark": 0,
        "size": 24
    }
    
    async def get_crf(self, mode=None):
        key = f"crf_{mode}" if mode else "crf"
        doc = await self.collection.find_one({"_id": key})
        return doc["value"] if doc else self.defaults["crf"]
    
    async def set_crf(self, value, mode=None):
        key = f"crf_{mode}" if mode else "crf"
        await self.collection.replace_one({"_id": key}, {"_id": key, "value": value}, upsert=True)

    async def get_size(self, mode=None):
        key = f"size_{mode}" if mode else "size"
        doc = await self.collection.find_one({"_id": key})
        return doc["value"] if doc else self.defaults["size"]
    
    async def set_size(self, value, mode=None):
        key = f"size_{mode}" if mode else "size"
        await self.collection.replace_one({"_id": key}, {"_id": key, "value": value}, upsert=True)
      
    async def get_watermark(self, mode=None):
        key = f"watermark_{mode}" if mode else "watermark"
        doc = await self.collection.find_one({"_id": key})
        value = doc["value"] if doc else self.defaults["watermark"]
        return None if value == 0 else value
    
    async def set_watermark(self, value, mode=None):
        key = f"watermark_{mode}" if mode else "watermark"
        await self.collection.replace_one({"_id": key}, {"_id": key, "value": value}, upsert=True)
    
    async def get_resolution(self, mode=None):
        key = f"resolution_{mode}" if mode else "resolution"
        doc = await self.collection.find_one({"_id": key})
        return doc["value"] if doc else self.defaults["resolution"]
    
    async def set_resolution(self, value, mode=None):
        key = f"resolution_{mode}" if mode else "resolution"
        await self.collection.replace_one({"_id": key}, {"_id": key, "value": value}, upsert=True)
    
    async def get_audio_b(self, mode=None):
        key = f"audio_b_{mode}" if mode else "audio_b"
        doc = await self.collection.find_one({"_id": key})
        return doc["value"] if doc else self.defaults["audio_b"]
    
    async def set_audio_b(self, value, mode=None):
        key = f"audio_b_{mode}" if mode else "audio_b"
        await self.collection.replace_one({"_id": key}, {"_id": key, "value": value}, upsert=True)
    
    async def get_preset(self, mode=None):
        key = f"preset_{mode}" if mode else "preset"
        doc = await self.collection.find_one({"_id": key})
        return doc["value"] if doc else self.defaults["preset"]
    
    async def set_preset(self, value, mode=None):
        key = f"preset_{mode}" if mode else "preset"
        await self.collection.replace_one({"_id": key}, {"_id": key, "value": value}, upsert=True)
    
    async def get_audio_codec(self, mode=None):
        key = f"audio_codec_{mode}" if mode else "audio_codec"
        doc = await self.collection.find_one({"_id": key})
        return doc["value"] if doc else self.defaults["audio_codec"]
    
    async def set_audio_codec(self, value, mode=None):
        key = f"audio_codec_{mode}" if mode else "audio_codec"
        await self.collection.replace_one({"_id": key}, {"_id": key, "value": value}, upsert=True)
    
    async def get_video_codec(self, mode=None):
        key = f"video_codec_{mode}" if mode else "video_codec"
        doc = await self.collection.find_one({"_id": key})
        return doc["value"] if doc else self.defaults["video_codec"]
    
    async def set_video_codec(self, value, mode=None):
        key = f"video_codec_{mode}" if mode else "video_codec"
        await self.collection.replace_one({"_id": key}, {"_id": key, "value": value}, upsert=True)
    
    async def get_video_bitrate(self, mode=None):
        key = f"video_bitrate_{mode}" if mode else "video_bitrate"
        doc = await self.collection.find_one({"_id": key})
        value = doc["value"] if doc else self.defaults["video_bitrate"]
        return None if value == 0 else value
    
    async def set_video_bitrate(self, value, mode=None):
        key = f"video_bitrate_{mode}" if mode else "video_bitrate"
        await self.collection.replace_one({"_id": key}, {"_id": key, "value": value}, upsert=True)

    async def get_bits(self, mode=None):
        key = f"bits_{mode}" if mode else "bits"
        doc = await self.collection.find_one({"_id": key})
        return doc["value"] if doc else self.defaults["bits"]
    
    async def set_bits(self, value, mode=None):
        key = f"bits_{mode}" if mode else "bits"
        await self.collection.replace_one({"_id": key}, {"_id": key, "value": value}, upsert=True)

    async def get_auth_users(self):
        doc = await self.collection.find_one({"_id": "auth_users"})
        return doc["users"] if doc and "users" in doc else []

    async def add_auth_user(self, user_id):
        await self.collection.update_one(
            {"_id": "auth_users"},
            {"$addToSet": {"users": user_id}},
            upsert=True
        )

    async def remove_auth_user(self, user_id):
        await self.collection.update_one(
            {"_id": "auth_users"},
            {"$pull": {"users": user_id}}
        )
            

db = Database()
