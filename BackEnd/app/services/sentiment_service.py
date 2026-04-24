import json
from groq import Groq
from app.core.config import settings
from app.models.profile import Comment, SentimentAnalysis

def analyze_post_acceptance(caption: str, comments: list[Comment]) -> tuple[list[Comment], SentimentAnalysis]:
    """
    Usa Groq LLM para analizar el sentimiento de cada comentario en contexto
    del caption del post, y generar un resumen de aceptación general.
    Retorna los comentarios enriquecidos con sentimiento + el análisis global.
    """
    if not comments:
        return comments, SentimentAnalysis(
            summary="No hay comentarios para analizar.",
            total_comments=0
        )
    
    # Construir el prompt con contexto del post
    comments_text = "\n".join([
        f'{i+1}. @{c.username}: "{c.text}"' 
        for i, c in enumerate(comments)
    ])
    
    prompt = f"""Analiza los siguientes comentarios de un post de Instagram.

CAPTION DEL POST:
"{caption or 'Sin caption'}"

COMENTARIOS:
{comments_text}

Responde ÚNICAMENTE con un JSON válido (sin markdown, sin ```json, sin texto adicional) con esta estructura exacta:
{{
  "comments": [
    {{"index": 1, "sentiment": "positive"}},
    {{"index": 2, "sentiment": "negative"}},
    {{"index": 3, "sentiment": "neutral"}}
  ],
  "summary": "Breve resumen en español (1-2 oraciones) del sentimiento general hacia el post"
}}

Reglas:
- "sentiment" solo puede ser: "positive", "negative", o "neutral"
- Considera el contexto del caption para entender mejor los comentarios
- Emojis positivos (❤️🔥👏😍🙌) cuentan como positivo
- Emojis negativos (😡👎💔😢) cuentan como negativo
- Comentarios muy cortos o ambiguos son "neutral"
- El summary debe ser en español
- Responde SOLO el JSON, nada más"""

    try:
        client = Groq(api_key=settings.GROQ_API_KEY)
        
        # Usar modo NO streaming para parsear JSON fácilmente
        completion = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {
                    "role": "system",
                    "content": "Eres un analista de sentimiento para redes sociales. Respondes ÚNICAMENTE con JSON válido, sin ningún texto adicional ni formateo markdown."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_completion_tokens=2048,
            top_p=1,
            stream=False,
            stop=None
        )
        
        raw_response = completion.choices[0].message.content.strip()
        print(f"[SentimentService] Respuesta cruda de Groq: {raw_response[:200]}...")
        
        # Limpiar posible markdown wrapping
        if raw_response.startswith("```"):
            raw_response = raw_response.split("\n", 1)[1] if "\n" in raw_response else raw_response
            if raw_response.endswith("```"):
                raw_response = raw_response[:-3].strip()
        
        result = json.loads(raw_response)
        
        # Enriquecer comentarios con sentimiento
        sentiment_map = {}
        for item in result.get("comments", []):
            idx = item.get("index", 0) - 1  # Convertir a 0-indexed
            sentiment_map[idx] = item.get("sentiment", "neutral")
        
        enriched_comments = []
        positive_count = 0
        negative_count = 0
        neutral_count = 0
        
        for i, comment in enumerate(comments):
            sentiment = sentiment_map.get(i, "neutral")
            enriched_comments.append(Comment(
                username=comment.username,
                text=comment.text,
                sentiment=sentiment
            ))
            if sentiment == "positive":
                positive_count += 1
            elif sentiment == "negative":
                negative_count += 1
            else:
                neutral_count += 1
        
        total = len(enriched_comments)
        # Score: positivos pesan 100%, neutrales 50%, negativos 0%
        acceptance_score = round(
            ((positive_count * 1.0 + neutral_count * 0.5) / total) * 100, 1
        ) if total > 0 else 0.0
        
        analysis = SentimentAnalysis(
            acceptance_score=acceptance_score,
            positive_count=positive_count,
            negative_count=negative_count,
            neutral_count=neutral_count,
            total_comments=total,
            summary=result.get("summary", "Análisis completado.")
        )
        
        print(f"[SentimentService] Análisis completado: Score={acceptance_score}% | +{positive_count} -{negative_count} ~{neutral_count}")
        return enriched_comments, analysis
        
    except json.JSONDecodeError as e:
        print(f"[SentimentService] Error parseando JSON de Groq: {e}")
        print(f"[SentimentService] Respuesta raw: {raw_response}")
        # Fallback: marcar todo como neutral
        return comments, SentimentAnalysis(
            acceptance_score=50.0,
            neutral_count=len(comments),
            total_comments=len(comments),
            summary="No se pudo analizar el sentimiento. Los comentarios se marcaron como neutrales."
        )
    except Exception as e:
        print(f"[SentimentService] Error llamando a Groq: {e}")
        return comments, SentimentAnalysis(
            acceptance_score=50.0,
            neutral_count=len(comments),
            total_comments=len(comments),
            summary=f"Error en el análisis de sentimiento: {str(e)}"
        )

def analyze_personality(profile_data: dict) -> str:
    """
    Usa toda la información disponible del perfil (bio, posts, conclusiones de comentarios)
    para generar un análisis psicológico/de personalidad de la persona.
    """
    username = profile_data.get("username", "desconocido")
    display_name = profile_data.get("display_name", "")
    bio = profile_data.get("biography", "")
    category = profile_data.get("category", "")
    
    # Recopilar información de posts y sus análisis de sentimiento
    posts_summary = []
    for i, post in enumerate(profile_data.get("recent_posts", [])[:5]):
        caption = post.get("caption", "Sin texto")
        sentiment_summary = post.get("sentiment_analysis", {}).get("summary", "")
        acceptance = post.get("sentiment_analysis", {}).get("acceptance_score", "N/A")
        
        post_info = f"Post {i+1}: '{caption}'"
        if sentiment_summary:
            post_info += f" | Reacción del público: {sentiment_summary} (Aceptación: {acceptance}%)"
        posts_summary.append(post_info)
    
    all_posts_text = "\n".join(posts_summary)
    
    prompt = f"""Basado en la siguiente información de un perfil de Instagram, realiza un análisis de personalidad y características de la persona detrás de la cuenta.

PERFIL: @{username} ({display_name})
BIOGRAFÍA: "{bio}"
CATEGORÍA: {category}

DATOS RECIENTES DE SUS PUBLICACIONES Y CÓMO REACCIONA SU AUDIENCIA:
{all_posts_text}

Por favor, proporciona un análisis estructurado en español (aprox. 150-200 palabras) que incluya:
1. Arquetipo o perfil general.
2. Intereses principales y valores que proyecta.
3. Estilo de comunicación y cómo es percibido por su comunidad.
4. Conclusión sobre su marca personal.

Responde con el texto del análisis directamente, sin preámbulos."""

    try:
        client = Groq(api_key=settings.GROQ_API_KEY)
        completion = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {
                    "role": "system",
                    "content": "Eres un experto psicólogo y analista de marketing digital especializado en marca personal y comportamiento en redes sociales."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.5,
            max_completion_tokens=2048,
        )
        
        analysis = completion.choices[0].message.content.strip()
        print(f"[SentimentService] Análisis de personalidad generado para @{username}")
        return analysis
        
    except Exception as e:
        print(f"[SentimentService] Error generando análisis de personalidad: {e}")
        return f"No se pudo generar el análisis de personalidad en este momento: {str(e)}"
