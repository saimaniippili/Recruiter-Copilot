import asyncio
from crawl4ai import AsyncWebCrawler

async def _fetch_url(url: str) -> str:
    async with AsyncWebCrawler(verbose=True) as crawler:
        result = await crawler.arun(url=url)
        return result.markdown

def fetch_jd_from_url(url: str) -> str:
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(_fetch_url(url))
