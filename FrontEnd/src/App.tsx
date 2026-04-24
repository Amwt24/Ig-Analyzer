import { useState, useEffect } from 'react';
import { Search, Loader2, AlertCircle, Sparkles, History, Clock, Image as ImageIcon, MessageSquare, TrendingUp, ThumbsUp, ThumbsDown, Minus, BarChart3, X, BrainCircuit, UserSearch } from 'lucide-react';
import axios from 'axios';
import './App.css';

function App() {
  const [username, setUsername] = useState('');
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState('');
  const [history, setHistory] = useState<any[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  
  // Estados para posts y comments
  const [loadingPosts, setLoadingPosts] = useState(false);
  const [posts, setPosts] = useState<any[]>([]);
  const [selectedPost, setSelectedPost] = useState<any>(null);
  const [loadingComments, setLoadingComments] = useState(false);
  const [comments, setComments] = useState<any[]>([]);
  const [sentimentAnalysis, setSentimentAnalysis] = useState<any>(null);

  // Estados para análisis de personalidad
  const [loadingPersonality, setLoadingPersonality] = useState(false);
  const [personalityResult, setPersonalityResult] = useState<string | null>(null);

  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  // Proxy para imágenes de Instagram CDN que bloquean requests cross-origin
  const proxyImg = (url: string | null | undefined) => {
    if (!url) return '';
    // Solo proxy URLs del CDN de Instagram/Facebook
    if (url.includes('fbcdn.net') || url.includes('cdninstagram.com') || url.includes('instagram.')) {
      return `${API_URL}/api/image-proxy?url=${encodeURIComponent(url)}`;
    }
    return url;
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim()) return;

    setLoading(true);
    setError('');
    setData(null);
    setShowHistory(false);
    setPosts([]);
    setSelectedPost(null);
    setComments([]);
    setSentimentAnalysis(null);
    setPersonalityResult(null);

    try {
      const response = await axios.get(`${API_URL}/api/profile/${username.trim()}`);
      if (response.data.error || response.data.status === "error") {
        setError(response.data.message || 'Ocurrió un error consultando la API');
      } else {
        // La API devuelve { status: "success", data: { username: ... } }
        const profileData = response.data.data || response.data;
        setData(profileData);
        if (profileData.personality_analysis) {
          setPersonalityResult(profileData.personality_analysis);
        }
      }
    } catch (err: any) {
      if (err.message === 'Network Error') {
        setError('El servidor Backend (FastAPI) no está corriendo en el puerto 8000.');
      } else {
        setError(err.response?.data?.detail || err.message || 'Se perdió la conexión con el servidor.');
      }
    } finally {
      setLoading(false);
    }
  };

  const loadHistory = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/history`);
      if (response.data.status === "success") {
        setHistory(response.data.data);
      }
    } catch (err) {
      console.error("Error loading history", err);
    }
  };

  useEffect(() => {
    if (showHistory) {
      loadHistory();
    }
  }, [showHistory]);

  const handleHistoryClick = (profileData: any) => {
    setData(profileData);
    setShowHistory(false);
    setUsername(profileData.username);
    setPosts(profileData.recent_posts || []);
    setSelectedPost(null);
    setComments([]);
    setSentimentAnalysis(null);
    setPersonalityResult(profileData.personality_analysis || null);
  };

  const analyzePersonality = async () => {
    if (!data?.username) return;
    setLoadingPersonality(true);
    try {
      const res = await axios.get(`${API_URL}/api/profile/${data.username}/personality`);
      if (res.data.status === "success") {
        setPersonalityResult(res.data.data);
      }
    } catch (err: any) {
      setError(err.message || 'Error al generar análisis de personalidad');
    } finally {
      setLoadingPersonality(false);
    }
  };

  const loadPosts = async () => {
    if (!data?.username) return;
    setLoadingPosts(true);
    try {
      const res = await axios.get(`${API_URL}/api/profile/${data.username}/posts`);
      if (res.data.status === "success") {
        setPosts(res.data.data);
      }
    } catch (err: any) {
      setError(err.message || 'Error al cargar posts');
    } finally {
      setLoadingPosts(false);
    }
  };

  const loadComments = async (post: any) => {
    setSelectedPost(post);
    setLoadingComments(true);
    setComments([]);
    setSentimentAnalysis(null);
    try {
      const res = await axios.get(
        `${API_URL}/api/post/comments?url=${encodeURIComponent(post.url)}&username=${data.username}&caption=${encodeURIComponent(post.caption || '')}`
      );
      if (res.data.status === "success") {
        setComments(res.data.data.comments || []);
        setSentimentAnalysis(res.data.data.sentiment_analysis || null);
      }
    } catch (err: any) {
      setError(err.message || 'Error al cargar comentarios');
    } finally {
      setLoadingComments(false);
    }
  };

  const getSentimentIcon = (sentiment: string) => {
    switch (sentiment) {
      case 'positive': return <ThumbsUp size={14} />;
      case 'negative': return <ThumbsDown size={14} />;
      default: return <Minus size={14} />;
    }
  };

  const getAcceptanceColor = (score: number) => {
    if (score >= 75) return '#22c55e';
    if (score >= 50) return '#eab308';
    if (score >= 25) return '#f97316';
    return '#ef4444';
  };

  const getAcceptanceLabel = (score: number) => {
    if (score >= 80) return 'Excelente';
    if (score >= 60) return 'Buena';
    if (score >= 40) return 'Moderada';
    if (score >= 20) return 'Baja';
    return 'Muy Baja';
  };

  return (
    <div className="app-container">
      <header className="hero-section">
        <h1>
          IG Scraper <Sparkles className="inline-block mb-3 ml-1" size={40} color="#a5b4fc" />
        </h1>
        <p>Introduce un nombre de usuario de Instagram para consultar su perfil público mediante scraping inteligente con Playwright.</p>
      </header>

      <form className="search-container" onSubmit={handleSearch}>
        <input
          type="text"
          className="search-input"
          placeholder="Ej: andersliinky, adorn_quran..."
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />
        <button 
          type="submit" 
          className="search-button"
          disabled={loading || !username.trim()}
        >
          {loading ? (
            <><Loader2 className="spin-icon" size={22} /> Scrapeando...</>
          ) : (
            <><Search size={22} /> Buscar Perfil</>
          )}
        </button>
      </form>

      <div className="action-buttons">
        <button 
          className={`toggle-history-btn ${showHistory ? 'active' : ''}`}
          onClick={() => setShowHistory(!showHistory)}
        >
          <History size={18} /> {showHistory ? 'Ocultar Historial' : 'Ver Historial de Búsquedas'}
        </button>
      </div>

      {error && (
        <div className="results-container">
          <div className="error-message">
            <AlertCircle size={28} />
            <p>{error}</p>
          </div>
        </div>
      )}

      {data && (
        <div className="results-container">
          <div className="glass-card profile-card">
            <div className="profile-header">
              <div className="profile-image-container">
                {data.profile_pic_url ? (
                  <img src={proxyImg(data.profile_pic_url)} alt={data.username} className="profile-image" referrerPolicy="no-referrer" />
                ) : (
                  <div className="profile-image-fallback">
                    {data.username.charAt(0).toUpperCase()}
                  </div>
                )}
              </div>
              <div className="profile-info">
                <h2>{data.display_name}</h2>
                <p className="handle">@{data.username}</p>
                {data.category && <span className="profile-category">{data.category}</span>}
                {data.biography && <div className="profile-biography">{data.biography}</div>}
                {data.external_url && (
                  <a href={data.external_url} target="_blank" rel="noreferrer" className="profile-link">
                    🔗 {data.external_url.replace(/^https?:\/\//, '').substring(0, 30)}...
                  </a>
                )}
              </div>
            </div>
            
            <div className="profile-stats">
              <div className="stat-item">
                <span className="stat-value">{data.followers}</span>
                <span className="stat-label">Seguidores</span>
              </div>
              <div className="stat-item">
                <span className="stat-value">{data.following}</span>
                <span className="stat-label">Seguidos</span>
              </div>
              <div className="stat-item">
                <span className="stat-value">{data.posts}</span>
                <span className="stat-label">Posts</span>
              </div>
              <div className="stat-item personality-btn-container">
                <button 
                  className="analyze-personality-btn" 
                  onClick={analyzePersonality}
                  disabled={loadingPersonality}
                >
                  {loadingPersonality ? <Loader2 className="spin-icon" size={18} /> : <BrainCircuit size={18} />}
                  <span>{personalityResult ? 'Re-analizar Personalidad' : 'Analizar Personalidad'}</span>
                </button>
              </div>
            </div>

            {/* Resultado de Personalidad */}
            {(personalityResult || loadingPersonality) && (
              <div className="personality-analysis-card">
                <div className="personality-card-header">
                  <UserSearch size={22} className="text-indigo-400" />
                  <h3>Perfil de Personalidad IA</h3>
                </div>
                {loadingPersonality ? (
                  <div className="personality-loading">
                    <Loader2 className="spin-icon" size={32} />
                    <p>Procesando información del perfil, posts y comentarios...</p>
                  </div>
                ) : (
                  <div className="personality-content">
                    <p>{personalityResult}</p>
                    <div className="personality-disclaimer">
                      * Este análisis es generado por IA basado únicamente en la actividad pública reciente.
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Sección de Posts */}
            <div className="posts-section">
              <div className="posts-header">
                <h3>Últimos Posts</h3>
                {posts.length === 0 && !loadingPosts && (
                  <button className="load-posts-btn" onClick={loadPosts}>
                    <ImageIcon size={18} /> Cargar Posts
                  </button>
                )}
              </div>

              {loadingPosts && (
                <div className="loading-spinner-container">
                  <Loader2 className="spin-icon" size={32} />
                  <p>Extrayendo posts de Instagram...</p>
                </div>
              )}

              {posts.length > 0 && (
                <div className="posts-grid">
                  {posts.map((post, idx) => (
                    <div key={idx} className="post-card" onClick={() => loadComments(post)}>
                      {post.image_url ? (
                         <img src={proxyImg(post.image_url)} alt="Post" className="post-thumbnail" referrerPolicy="no-referrer" />
                      ) : (
                         <div className="post-thumbnail-fallback"><ImageIcon size={32} /></div>
                      )}
                      <div className="post-overlay">
                         <BarChart3 size={24} />
                         <span>Analizar Post</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Modal de Análisis de Post */}
      {selectedPost && (
        <div className="modal-overlay" onClick={() => { setSelectedPost(null); setSentimentAnalysis(null); }}>
          <div className="modal-content analysis-modal" onClick={e => e.stopPropagation()}>
            <button className="close-modal" onClick={() => { setSelectedPost(null); setSentimentAnalysis(null); }}>
              <X size={20} />
            </button>
            
            {/* Header del modal con imagen y caption */}
            <div className="modal-post-header">
              <div className="modal-post-image">
                {selectedPost.image_url ? (
                  <img src={proxyImg(selectedPost.image_url)} alt="Post" referrerPolicy="no-referrer" />
                ) : (
                  <div className="modal-post-image-fallback"><ImageIcon size={40} /></div>
                )}
              </div>
              <div className="modal-post-info">
                <h3>Análisis de Aceptación</h3>
                {selectedPost.caption && (
                  <p className="modal-caption">{selectedPost.caption.substring(0, 150)}{selectedPost.caption.length > 150 ? '...' : ''}</p>
                )}
                <a href={selectedPost.url} target="_blank" rel="noreferrer" className="view-post-link">
                  Ver en Instagram ↗
                </a>
              </div>
            </div>
            
            {loadingComments ? (
              <div className="loading-spinner-container analysis-loading">
                <Loader2 className="spin-icon" size={36} />
                <p>Extrayendo comentarios y analizando sentimiento...</p>
                <span className="loading-subtext">Esto puede tomar unos segundos</span>
              </div>
            ) : (
              <>
                {/* Barra de Aceptación */}
                {sentimentAnalysis && (
                  <div className="sentiment-section">
                    <div className="acceptance-header">
                      <div className="acceptance-score-display">
                        <TrendingUp size={20} color={getAcceptanceColor(sentimentAnalysis.acceptance_score)} />
                        <span className="acceptance-score" style={{ color: getAcceptanceColor(sentimentAnalysis.acceptance_score) }}>
                          {sentimentAnalysis.acceptance_score}%
                        </span>
                        <span className="acceptance-label" style={{ color: getAcceptanceColor(sentimentAnalysis.acceptance_score) }}>
                          {getAcceptanceLabel(sentimentAnalysis.acceptance_score)}
                        </span>
                      </div>
                    </div>
                    
                    <div className="acceptance-bar-container">
                      <div 
                        className="acceptance-bar-fill"
                        style={{ 
                          width: `${sentimentAnalysis.acceptance_score}%`,
                          background: `linear-gradient(90deg, ${getAcceptanceColor(sentimentAnalysis.acceptance_score)}88, ${getAcceptanceColor(sentimentAnalysis.acceptance_score)})`
                        }}
                      />
                    </div>
                    
                    <div className="sentiment-counters">
                      <div className="counter positive">
                        <ThumbsUp size={14} />
                        <span>{sentimentAnalysis.positive_count} Positivos</span>
                      </div>
                      <div className="counter neutral">
                        <Minus size={14} />
                        <span>{sentimentAnalysis.neutral_count} Neutros</span>
                      </div>
                      <div className="counter negative">
                        <ThumbsDown size={14} />
                        <span>{sentimentAnalysis.negative_count} Negativos</span>
                      </div>
                    </div>
                    
                    {sentimentAnalysis.summary && (
                      <div className="sentiment-summary">
                        <p>{sentimentAnalysis.summary}</p>
                      </div>
                    )}
                  </div>
                )}

                {/* Lista de Comentarios */}
                {comments.length > 0 ? (
                  <div className="comments-list">
                    <h4 className="comments-title">
                      <MessageSquare size={16} /> Comentarios ({comments.length})
                    </h4>
                    {comments.map((c, i) => (
                      <div key={i} className={`comment-item comment-${c.sentiment || 'neutral'}`}>
                        <div className="comment-header">
                          <strong>@{c.username}</strong>
                          <span className={`sentiment-badge badge-${c.sentiment || 'neutral'}`}>
                            {getSentimentIcon(c.sentiment || 'neutral')}
                            {c.sentiment === 'positive' ? 'Positivo' : c.sentiment === 'negative' ? 'Negativo' : 'Neutro'}
                          </span>
                        </div>
                        <p>{c.text}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="no-comments">No se encontraron comentarios para este post.</p>
                )}
              </>
            )}
          </div>
        </div>
      )}

      {showHistory && !loading && (
        <div className="results-container history-container">
          <div className="glass-card">
            <h2 className="history-title"><Clock size={24} /> Búsquedas Recientes</h2>
            {history.length === 0 ? (
              <p className="no-history">No hay perfiles guardados aún.</p>
            ) : (
              <div className="history-grid">
                {history.map((item, index) => (
                  <div key={index} className="history-card" onClick={() => handleHistoryClick(item)}>
                    <div className="history-card-header">
                      {item.profile_pic_url ? (
                        <img src={proxyImg(item.profile_pic_url)} alt={item.username} className="history-img" referrerPolicy="no-referrer" />
                      ) : (
                        <div className="history-fallback">{item.username.charAt(0).toUpperCase()}</div>
                      )}
                      <div>
                        <h3>{item.display_name}</h3>
                        <p>@{item.username}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
