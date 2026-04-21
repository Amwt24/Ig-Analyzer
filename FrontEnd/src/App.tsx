import { useState, useEffect } from 'react';
import { Search, Loader2, AlertCircle, Sparkles, History, Clock } from 'lucide-react';
import axios from 'axios';
import './App.css';

function App() {
  const [username, setUsername] = useState('');
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState('');
  const [history, setHistory] = useState<any[]>([]);
  const [showHistory, setShowHistory] = useState(false);

  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim()) return;

    setLoading(true);
    setError('');
    setData(null);
    setShowHistory(false);

    try {
      const response = await axios.get(`${API_URL}/api/profile/${username.trim()}`);
      if (response.data.error || response.data.status === "error") {
        setError(response.data.message || 'Ocurrió un error consultando la API');
      } else {
        // La API devuelve { status: "success", data: { username: ... } }
        setData(response.data.data || response.data);
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
  };

  return (
    <div className="app-container">
      <header className="hero-section">
        <h1>
          IG Scraper <Sparkles className="inline-block mb-3 ml-1" size={40} color="#a5b4fc" />
        </h1>
        <p>Introduce un nombre de usuario de Instagram para consultar su perfil público utilizando un proxy seguro de RapidAPI sin penalización de IP.</p>
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
                  <img src={data.profile_pic_url} alt={data.username} className="profile-image" />
                ) : (
                  <div className="profile-image-fallback">
                    {data.username.charAt(0).toUpperCase()}
                  </div>
                )}
              </div>
              <div className="profile-info">
                <h2>{data.display_name}</h2>
                <p className="handle">@{data.username}</p>
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
            </div>
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
                        <img src={item.profile_pic_url} alt={item.username} className="history-img" />
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
