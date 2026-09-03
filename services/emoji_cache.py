import os
import aiohttp
import logging
from aiogram import Bot
from config.emojis import EMOJI_IDS

logger = logging.getLogger(__name__)

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "webapp", "emojis")

async def cache_custom_emojis(bot: Bot):
    """
    Downloads and caches Telegram custom emoji webp thumbnails/stickers locally
    so the Mini App can display the exact animated/premium custom emojis.
    """
    os.makedirs(CACHE_DIR, exist_ok=True)
    emoji_ids = list(set(EMOJI_IDS.values()))
    
    # Process in chunks of 50 (Telegram limit)
    chunk_size = 50
    for i in range(0, len(emoji_ids), chunk_size):
        chunk = emoji_ids[i:i + chunk_size]
        try:
            stickers = await bot.get_custom_emoji_stickers(custom_emoji_ids=chunk)
            for sticker in stickers:
                eid = sticker.custom_emoji_id
                target_file = os.path.join(CACHE_DIR, f"{eid}.webp")
                if os.path.exists(target_file):
                    continue

                file_id = sticker.thumbnail.file_id if sticker.thumbnail else sticker.file_id
                try:
                    f = await bot.get_file(file_id)
                    download_url = f"https://api.telegram.org/file/bot{bot.token}/{f.file_path}"
                    async with aiohttp.ClientSession() as session:
                        async with session.get(download_url) as resp:
                            if resp.status == 200:
                                with open(target_file, "wb") as out:
                                    out.write(await resp.read())
                except Exception as e:
                    logger.debug(f"Could not download emoji {eid}: {e}")
        except Exception as e:
            logger.warning(f"Error fetching custom emoji batch: {e}")

    logger.info(f"Custom emoji cache ready in {CACHE_DIR}")
