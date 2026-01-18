from bot.get_cfg import get_config

class Config(object):
    #Session
    SESSION_NAME = get_config("SESSION_NAME", "EncoderX") 
    #Telegram Credentials 
    APP_ID = int(get_config("APP_ID", "28891870"))
    API_HASH = get_config("API_HASH", "ffc3794690bf254d2867ac58fd293a60")

    # Bot Credentials 
    TG_BOT_TOKEN = get_config("TG_BOT_TOKEN", "8347616055:AAHxACwlMceprKFi7opb1XTGh3kZzlVcsCE")
    BOT_USERNAME = get_config("BOT_USERNAME", "Oaid_enc_bot") #Without @

    # Heroku
    HEROKU_API_KEY = get_config("HEROKU_API_KEY", None)
    HEROKU_APP_NAME = get_config("HEROKU_APP_NAME", None)
    UPSTREAM_REPO = get_config("UPSTREAM_REPO", "https://github.com/AbhiMod/hk-pvt-encoder")

    # User or group id (Seperated by commas 
    AUTH_USERS = [7660990923]

    #Channels
    LOG_CHANNEL = get_config("LOG_CHANNEL", "Lod_krishna")
    UPDATES_CHANNEL = get_config("UPDATES_CHANNEL", None) # Without `@` LOL

    #Mongo DB: (Added by @Telegram_Guyz in github 🌚) 
    MONGO_URI = get_config("MONGO_URI", "mongodb+srv://raj:krishna@cluster0.eq8xrjs.mongodb.net/") #Required 
    DB_NAME = get_config("DB_NAME", "TGguy") #Required
    COLLECTION_NAME = get_config("COLLECTION_NAME", "Stores") #Required

    
    # Download location of your server 
    DOWNLOAD_LOCATION = get_config("DOWNLOAD_LOCATION", "/app/downloads")
    
    # Telegram maximum file upload size
    MAX_FILE_SIZE = 4194304000
    TG_MAX_FILE_SIZE = 4194304000
    FREE_USER_MAX_FILE_SIZE = 4194304000
    UPDATE_INTERVAL = 7
    
    # default thumbnail to be used in the videos
    DEF_THUMB_NAIL_VID_S = get_config("DEF_THUMB_NAIL_VID_S", "https://envs.sh/CQU.jpg")
    
    # proxy for accessing youtube-dl in GeoRestricted Areas
    # Get your own proxy from https://github.com/rg3/youtube-dl/issues/1091#issuecomment-230163061
    HTTP_PROXY = get_config("HTTP_PROXY", None)
    # maximum message length in Telegram
    MAX_MESSAGE_LENGTH = 4096
    
    # add config vars for the display progress
    FINISHED_PROGRESS_STR = get_config("FINISHED_PROGRESS_STR", "▣")
    UN_FINISHED_PROGRESS_STR = get_config("UN_FINISHED_PROGRESS_STR", "▢")
    LOG_FILE_ZZGEVC = get_config("LOG_FILE_ZZGEVC", "Log.txt")
    SHOULD_USE_BUTTONS = get_config("SHOULD_USE_BUTTONS", False)
