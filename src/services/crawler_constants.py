DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
DEFAULT_HEADERS = {
    "User-Agent": DEFAULT_USER_AGENT,
    "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
}

THUMBNAIL_SIZE = (300, 300)
THUMBNAIL_QUALITY = 85
THUMBNAIL_FORMAT = "JPEG"

MAX_RETRIES = 3
REQUEST_TIMEOUT = 15

BLOG_TYPE_NAVER = "naver"
BLOG_TYPE_KAKAO = "kakao"
BLOG_TYPE_DEVOCEAN = "devocean"
BLOG_TYPE_GENERIC = "generic"
