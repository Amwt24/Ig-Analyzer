import os
import scrapy
import json
from dotenv import load_dotenv, find_dotenv
from ScraperIG.items import InstagramProfileItem, InstagramPostItem

# Cargar las variables de entorno desde el archivo .env
load_dotenv(find_dotenv())

class InstagramSpider(scrapy.Spider):
    name = "instagram"
    allowed_domains = ["instagram.com"]
    
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "X-IG-App-ID": "936619743392459",
        "X-ASBD-ID": "129477",
        "X-IG-WWW-Claim": "0",
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "*/*",
        "Referer": "https://www.instagram.com/",
    }

    def __init__(self, target_user=None, *args, **kwargs):
        super(InstagramSpider, self).__init__(*args, **kwargs)
        self.target_user = target_user

    def start_requests(self):
        if not self.target_user:
            self.logger.error("Debe proporcionar un usuario objetivo: -a target_user=username")
            return

        # Parseamos la cadena de cookies del archivo .env
        cookies_str = os.getenv("IG_COOKIE_STRING", "")
        cookies = {}
        if cookies_str:
            for cookie in cookies_str.split(";"):
                if "=" in cookie:
                    key, value = cookie.strip().split("=", 1)
                    cookies[key] = value

        if not cookies:
            self.logger.warning("No se ha configurado IG_COOKIE_STRING en el archivo .env. La peticion podría fallar.")

        url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username={self.target_user}"
        yield scrapy.Request(
            url, 
            headers=self.HEADERS, 
            cookies=cookies, 
            meta={'handle_httpstatus_list': [401, 403, 404, 429]}, # Permitimos estos códigos para manejarlos manualmente
            callback=self.parse_profile
        )

    def parse_profile(self, response):
        if response.status == 429:
            self.logger.error("Instagram bloqueó la petición con HTTP 429 (Too Many Requests). Tus cookies han expirado o Instagram está limitando tu IP.")
            return
            
        if response.status != 200:
            self.logger.error(f"Error HTTP: {response.status}. Puede que las cookies hayan expirado o el usuario no exista.")
            return

        try:
            data = json.loads(response.text)
        except json.JSONDecodeError:
            self.logger.error("Error al decodificar JSON. Instagram puede estar devolviendo HTML (posible bloqueo o login requerido).")
            self.logger.debug(f"Cuerpo de respuesta: {response.text[:500]}")
            return

        user_data = data.get("data", {}).get("user", {})
        
        if not user_data:
            self.logger.error("La API respondió, pero no se encontró la clave 'user'. Verifique el nombre de usuario o si la cuenta es privada.")
            return

        profile = InstagramProfileItem()
        profile["username"] = user_data.get("username")
        profile["full_name"] = user_data.get("full_name")
        profile["bio"] = user_data.get("biography")
        profile["followers_count"] = user_data.get("edge_followed_by", {}).get("count")
        profile["following_count"] = user_data.get("edge_follow", {}).get("count")
        profile["posts_count"] = user_data.get("edge_owner_to_timeline_media", {}).get("count")
        profile["profile_pic_url"] = user_data.get("profile_pic_url_hd")
        profile["is_private"] = user_data.get("is_private")
        profile["is_verified"] = user_data.get("is_verified")
        
        yield profile

        # Procesar publicaciones iniciales
        posts = user_data.get("edge_owner_to_timeline_media", {}).get("edges", [])
        for edge in posts:
            node = edge.get("node", {})
            post = InstagramPostItem()
            post["post_id"] = node.get("id")
            post["shortcode"] = node.get("shortcode")
            post["display_url"] = node.get("display_url")
            
            caption_edges = node.get("edge_media_to_caption", {}).get("edges", [])
            post["caption"] = caption_edges[0].get("node", {}).get("text") if caption_edges else ""
            
            post["likes_count"] = node.get("edge_liked_by", {}).get("count")
            post["comments_count"] = node.get("edge_media_to_comment", {}).get("count")
            post["timestamp"] = node.get("taken_at_timestamp")
            post["is_video"] = node.get("is_video")
            post["video_url"] = node.get("video_url")
            
            yield post

        # Si hay más páginas, se podría implementar la paginación aquí usando el 'end_cursor'
        # y el ID de usuario (user_data.get('id')) llamando a otro endpoint de GraphQL.
