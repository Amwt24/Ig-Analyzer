import scrapy

class InstagramProfileItem(scrapy.Item):
    username = scrapy.Field()
    full_name = scrapy.Field()
    bio = scrapy.Field()
    followers_count = scrapy.Field()
    following_count = scrapy.Field()
    posts_count = scrapy.Field()
    profile_pic_url = scrapy.Field()
    is_private = scrapy.Field()
    is_verified = scrapy.Field()

class InstagramPostItem(scrapy.Item):
    post_id = scrapy.Field()
    shortcode = scrapy.Field()
    display_url = scrapy.Field()
    caption = scrapy.Field()
    likes_count = scrapy.Field()
    comments_count = scrapy.Field()
    timestamp = scrapy.Field()
    video_url = scrapy.Field()
    is_video = scrapy.Field()
