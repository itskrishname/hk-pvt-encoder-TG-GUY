from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URI, MONGO_DB, MONGO_COLLECTION

class SettingsDB:
    def __init__(self):
        # Connect to MongoDB using Motor
        self.client = AsyncIOMotorClient(MONGO_URI)
        self.db = self.client[MONGO_DB]
        self.collection = self.db[MONGO_COLLECTION]

        # Default values
        self.defaults = {
            "crf": "30",
            "preset": "veryfast",
            "resolution": "1280x720",
            "audio_b": "64k",
            "audio_codec": "aac",
            "video_codec": "libx264",
            "video_bitrate": None,  # 0 will be converted to None
            "watermark": None
        }

    async def init_config(self):
        """Ensure a single config document exists"""
        doc = await self.collection.find_one({"_id": "config"})
        if not doc:
            await self.collection.insert_one({"_id": "config", **self.defaults})

    async def set_value(self, key: str, value):
        """Set a specific setting value"""
        if key not in self.defaults:
            raise ValueError(f"Invalid key: {key}")
        # Convert 0 to None for video_bitrate
        if key == "video_bitrate" and value == 0:
            value = None
        await self.collection.update_one({"_id": "config"}, {"$set": {key: value}}, upsert=True)

    async def get_value(self, key: str):
        """Get current value of a setting"""
        doc = await self.collection.find_one({"_id": "config"})
        if not doc:
            return self.defaults.get(key)
        return doc.get(key, self.defaults.get(key))

    # Optional: individual helpers
    async def set_crf(self, value: str):
        await self.set_value("crf", value)

    async def get_crf(self):
        return await self.get_value("crf")

    async def set_preset(self, value: str):
        await self.set_value("preset", value)

    async def get_preset(self):
        return await self.get_value("preset")

    async def set_resolution(self, value: str):
        await self.set_value("resolution", value)

    async def get_resolution(self):
        return await self.get_value("resolution")

    async def set_audio_b(self, value: str):
        await self.set_value("audio_b", value)

    async def get_audio_b(self):
        return await self.get_value("audio_b")

    async def set_audio_codec(self, value: str):
        await self.set_value("audio_codec", value)

    async def get_audio_codec(self):
        return await self.get_value("audio_codec")

    async def set_video_codec(self, value: str):
        await self.set_value("video_codec", value)

    async def get_video_codec(self):
        return await self.get_value("video_codec")

    async def set_video_bitrate(self, value: int):
        await self.set_value("video_bitrate", value)

    async def get_video_bitrate(self):
        return await self.get_value("video_bitrate")

    async def set_watermark(self, value: str | None):
        await self.set_value("watermark", value)

    async def get_watermark(self):
        return await self.get_value("watermark")

db = SettingsDB()
