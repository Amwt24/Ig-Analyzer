import { useState } from 'react';
import { Search, Loader2, AlertCircle, Sparkles } from 'lucide-react';
import axios from 'axios';
import './App.css';

function App() {
  const [username, setUsername] = useState('');
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState('');

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim()) return;

    setLoading(true);
    setError('');
    setData(null);

    try {
      const response = await axios.get(`http://localhost:8000/api/profile/${username.trim()}`);
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
    </div>
  );
}

export default App;
