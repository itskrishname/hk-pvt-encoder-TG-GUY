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
        "preset": "faster",
        "resolution": "640x360",
        "audio_b": "32k",
        "audio_codec": "aac",
        "video_codec": "libx265",
        "video_bitrate": 0,
        "bits": "8",
        "watermark": 0,
        "size": 24
    }
    
    async def get_crf(self):
        doc = await self.collection.find_one({"_id": "crf"})
        return doc["value"] if doc else self.defaults["crf"]
    
    async def set_crf(self, value):
        await self.collection.replace_one({"_id": "crf"}, {"_id": "crf", "value": value}, upsert=True)

    async def get_size(self):
        doc = await self.collection.find_one({"_id": "size"})
        return doc["value"] if doc else self.defaults["size"]
    
    async def set_size(self, value):
        await self.collection.replace_one({"_id": "size"}, {"_id": "size", "value": value}, upsert=True)
      
    async def get_watermark(self):
        doc = await self.collection.find_one({"_id": "watermark"})
        value = doc["value"] if doc else self.defaults["watermark"]
        return None if value == 0 else value
    
    async def set_watermark(self, value):
        await self.collection.replace_one({"_id": "watermark"}, {"_id": "watermark", "value": value}, upsert=True)
    
    async def get_resolution(self):
        doc = await self.collection.find_one({"_id": "resolution"})
        return doc["value"] if doc else self.defaults["resolution"]
    
    async def set_resolution(self, value):
        await self.collection.replace_one({"_id": "resolution"}, {"_id": "resolution", "value": value}, upsert=True)
    
    async def get_audio_b(self):
        doc = await self.collection.find_one({"_id": "audio_b"})
        return doc["value"] if doc else self.defaults["audio_b"]
    
    async def set_audio_b(self, value):
        await self.collection.replace_one({"_id": "audio_b"}, {"_id": "audio_b", "value": value}, upsert=True)
    
    async def get_preset(self):
        doc = await self.collection.find_one({"_id": "preset"})
        return doc["value"] if doc else self.defaults["preset"]
    
    async def set_preset(self, value):
        await self.collection.replace_one({"_id": "preset"}, {"_id": "preset", "value": value}, upsert=True)
    
    async def get_audio_codec(self):
        doc = await self.collection.find_one({"_id": "audio_codec"})
        return doc["value"] if doc else self.defaults["audio_codec"]
    
    async def set_audio_codec(self, value):
        await self.collection.replace_one({"_id": "audio_codec"}, {"_id": "audio_codec", "value": value}, upsert=True)
    
    async def get_video_codec(self):
        doc = await self.collection.find_one({"_id": "video_codec"})
        return doc["value"] if doc else self.defaults["video_codec"]
    
    async def set_video_codec(self, value):
        await self.collection.replace_one({"_id": "video_codec"}, {"_id": "video_codec", "value": value}, upsert=True)
    
    async def get_video_bitrate(self):
        doc = await self.collection.find_one({"_id": "video_bitrate"})
        value = doc["value"] if doc else self.defaults["video_bitrate"]
        return None if value == 0 else value
    
    async def set_video_bitrate(self, value):
        await self.collection.replace_one({"_id": "video_bitrate"}, {"_id": "video_bitrate", "value": value}, upsert=True)

    async def get_bits(self):
        doc = await self.collection.find_one({"_id": "bits"})
        return doc["value"] if doc else self.defaults["bits"]
    
    async def set_bits(self, value):
        await self.collection.replace_one({"_id": "bits"}, {"_id": "bits", "value": value}, upsert=True)
            

db = Database()
