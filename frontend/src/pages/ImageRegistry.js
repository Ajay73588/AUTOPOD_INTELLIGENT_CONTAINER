import React, { useState, useEffect } from 'react';
import { apiService } from '../services/api';
import '../styles/ImageRegistry.css';

const ImageRegistry = () => {
  const [activeTab, setActiveTab] = useState('local');
  const [localImages, setLocalImages] = useState([]);
  const [searchResults, setSearchResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [pullImageName, setPullImageName] = useState('');
  const [statusMessage, setStatusMessage] = useState('');
  
  // Docker Hub Authentication States
  const [dockerUsername, setDockerUsername] = useState('');
  const [dockerPassword, setDockerPassword] = useState('');
  const [isDockerLoggedIn, setIsDockerLoggedIn] = useState(false);
  const [checkingLogin, setCheckingLogin] = useState(false);
  const [showLoginForm, setShowLoginForm] = useState(false);

  useEffect(() => {
    if (activeTab === 'local') {
      fetchLocalImages();
    }
    checkDockerLoginStatus();
  }, [activeTab]);

  // Docker Hub Authentication Functions
  const checkDockerLoginStatus = async () => {
    try {
      setCheckingLogin(true);
      const response = await apiService.checkDockerLogin();
      if (response.data.success) {
        setIsDockerLoggedIn(response.data.logged_in);
        if (response.data.logged_in && response.data.username) {
          setDockerUsername(response.data.username);
        }
      }
    } catch (error) {
      console.error('Error checking Docker login:', error);
      setIsDockerLoggedIn(false);
    } finally {
      setCheckingLogin(false);
    }
  };

  const handleDockerLogin = async () => {
    if (!dockerUsername || !dockerPassword) {
      setStatusMessage('❌ Please enter both username and password');
      return;
    }

    try {
      setLoading(true);
      setStatusMessage('🔐 Logging in to Docker Hub...');
      
      const response = await apiService.dockerLogin({
        username: dockerUsername,
        password: dockerPassword,
        registry: "docker.io"
      });

      if (response.data.success) {
        setIsDockerLoggedIn(true);
        setStatusMessage('✅ Successfully logged in to Docker Hub!');
        setShowLoginForm(false);
        setDockerPassword(''); // Clear password for security
      } else {
        setStatusMessage(`❌ Login failed: ${response.data.error}`);
      }
    } catch (error) {
      console.error('Error logging in to Docker:', error);
      setStatusMessage(`❌ Login error: ${error.response?.data?.error || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDockerLogout = async () => {
    try {
      setStatusMessage('🔐 Logging out from Docker Hub...');
      const response = await apiService.dockerLogout();
      
      if (response.data.success) {
        setIsDockerLoggedIn(false);
        setStatusMessage('✅ Successfully logged out from Docker Hub!');
        setDockerUsername('');
        setDockerPassword('');
      }
    } catch (error) {
      console.error('Error logging out from Docker:', error);
      setStatusMessage(`❌ Logout error: ${error.response?.data?.error || error.message}`);
    }
  };

  const fetchLocalImages = async () => {
    try {
      setLoading(true);
      const response = await apiService.getImages();
      if (response.data.success) {
        setLocalImages(response.data.data || []);
      }
    } catch (error) {
      console.error('Error fetching local images:', error);
      setStatusMessage('❌ Error fetching local images');
    } finally {
      setLoading(false);
    }
  };

  const searchRegistry = async () => {
    if (!searchQuery.trim()) return;
    
    try {
      setLoading(true);
      const response = await apiService.searchImages(searchQuery);
      if (response.data.success) {
        setSearchResults(response.data.data || []);
      }
    } catch (error) {
      console.error('Error searching registry:', error);
      setStatusMessage('❌ Error searching registry');
    } finally {
      setLoading(false);
    }
  };

  const pullImage = async () => {
    if (!pullImageName.trim()) return;
    
    try {
      setStatusMessage(`⬇️ Pulling image: ${pullImageName}...`);
      const response = await apiService.pullImage(pullImageName);
      if (response.data.success) {
        setStatusMessage(`✅ Image pulled successfully: ${pullImageName}`);
        setPullImageName('');
        fetchLocalImages();
      } else {
        setStatusMessage(`❌ Failed to pull image: ${response.data.error}`);
      }
    } catch (error) {
      console.error('Error pulling image:', error);
      setStatusMessage('❌ Error pulling image');
    }
  };

  const removeImage = async (imageName) => {
    if (!window.confirm(`Are you sure you want to remove image ${imageName}?`)) return;
    
    try {
      setStatusMessage(`🗑️ Removing image: ${imageName}...`);
      const response = await apiService.removeImage(imageName);
      if (response.data.success) {
        setStatusMessage(`✅ Image removed successfully`);
        fetchLocalImages();
      } else {
        setStatusMessage(`❌ Failed to remove image: ${response.data.error}`);
      }
    } catch (error) {
      console.error('Error removing image:', error);
      setStatusMessage('❌ Error removing image');
    }
  };

  const formatImageSize = (size) => {
    if (!size) return 'N/A';
    const sizeInMB = size / (1024 * 1024);
    return sizeInMB > 1024 
      ? `${(sizeInMB / 1024).toFixed(2)} GB` 
      : `${sizeInMB.toFixed(2)} MB`;
  };

  const formatDate = (timestamp) => {
    if (!timestamp) return 'N/A';
    return new Date(timestamp * 1000).toLocaleDateString();
  };

  return (
    <div className="image-registry">
      <div className="page-header">
        <h1>📦 Container Registry</h1>
        <p>Manage images, search registries, and pull/push containers</p>
        
        {/* Docker Hub Status - Same as ContainerManagement */}
        <div className="docker-status">
          <div className={`status-badge ${isDockerLoggedIn ? 'logged-in' : 'logged-out'}`}>
            {checkingLogin ? (
              <span>🔍 Checking Docker Hub status...</span>
            ) : isDockerLoggedIn ? (
              <div className="status-content">
                <span className="status-icon">✅</span>
                <span className="status-text">Logged in as: {dockerUsername}</span>
                <button 
                  onClick={handleDockerLogout}
                  className="logout-btn"
                  title="Logout from Docker Hub"
                >
                  🚪 Logout
                </button>
              </div>
            ) : (
              <div className="status-content">
                <span className="status-icon">❌</span>
                <span className="status-text">Not logged in to Docker Hub</span>
                <button 
                  onClick={() => setShowLoginForm(!showLoginForm)}
                  className="login-toggle-btn"
                >
                  {showLoginForm ? 'Cancel' : '🔐 Login'}
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Docker Login Form - Same as ContainerManagement */}
      {showLoginForm && !isDockerLoggedIn && (
        <div className="docker-login-form">
          <div className="login-card">
            <h3>🔐 Docker Hub Login</h3>
            <div className="form-group">
              <label>Username:</label>
              <input
                type="text"
                value={dockerUsername}
                onChange={(e) => setDockerUsername(e.target.value)}
                className="form-input"
                placeholder="your-dockerhub-username"
              />
            </div>
            <div className="form-group">
              <label>Password:</label>
              <input
                type="password"
                value={dockerPassword}
                onChange={(e) => setDockerPassword(e.target.value)}
                className="form-input"
                placeholder="your-dockerhub-password"
              />
            </div>
            <div className="login-actions">
              <button 
                onClick={handleDockerLogin}
                disabled={!dockerUsername || !dockerPassword || loading}
                className="btn btn-primary"
              >
                {loading ? '🔄 Logging in...' : '🔐 Login to Docker Hub'}
              </button>
              <button 
                onClick={() => setShowLoginForm(false)}
                className="btn btn-secondary"
              >
                Cancel
              </button>
            </div>
            <div className="login-note">
              <p>💡 Your credentials are sent securely to the backend.</p>
            </div>
          </div>
        </div>
      )}

      {/* Status Message */}
      {statusMessage && (
        <div className={`status-message ${statusMessage.includes('✅') ? 'success' : statusMessage.includes('❌') ? 'error' : 'info'}`}>
          {statusMessage}
        </div>
      )}

      {/* Tabs */}
      <div className="registry-tabs">
        <button 
          className={`tab-btn ${activeTab === 'local' ? 'active' : ''}`}
          onClick={() => setActiveTab('local')}
        >
          <span className="tab-icon">💾</span>
          <span className="tab-text">Local Images ({localImages.length})</span>
        </button>
        <button 
          className={`tab-btn ${activeTab === 'search' ? 'active' : ''}`}
          onClick={() => setActiveTab('search')}
        >
          <span className="tab-icon">🔍</span>
          <span className="tab-text">Search Registry</span>
        </button>
        <button 
          className={`tab-btn ${activeTab === 'manage' ? 'active' : ''}`}
          onClick={() => setActiveTab('manage')}
        >
          <span className="tab-icon">⬇️</span>
          <span className="tab-text">Pull Image</span>
        </button>
      </div>

      {/* Local Images Tab */}
      {activeTab === 'local' && (
        <div className="registry-tab active">
          <div className="tab-header">
            <h2>💾 Local Images</h2>
            <div className="tab-actions">
              <button className="btn btn-secondary" onClick={fetchLocalImages} disabled={loading}>
                <span className="btn-icon">🔄</span>
                <span className="btn-text">Refresh</span>
              </button>
            </div>
          </div>

          {loading ? (
            <div className="loading-state">
              <div className="loading-spinner"></div>
              <p>Loading local images...</p>
            </div>
          ) : localImages.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">📦</div>
              <h3>No Local Images</h3>
              <p>Pull an image from the registry to get started.</p>
              <button 
                className="btn btn-primary"
                onClick={() => setActiveTab('manage')}
              >
                ⬇️ Pull Your First Image
              </button>
            </div>
          ) : (
            <div className="images-grid">
              {localImages.map((image, index) => (
                <div key={index} className="image-card">
                  <div className="image-header">
                    <div className="image-name">{image.RepoTags?.[0] || image.Id?.substring(0, 12)}</div>
                    <div className="image-size">{formatImageSize(image.Size)}</div>
                  </div>
                  <div className="image-details">
                    <div className="detail-item">
                      <span className="detail-label">ID:</span>
                      <span className="detail-value">{image.Id?.substring(0, 12) || 'N/A'}</span>
                    </div>
                    <div className="detail-item">
                      <span className="detail-label">Created:</span>
                      <span className="detail-value">{formatDate(image.Created)}</span>
                    </div>
                    <div className="detail-item">
                      <span className="detail-label">Architecture:</span>
                      <span className="detail-value">{image.Architecture || 'N/A'}</span>
                    </div>
                  </div>
                  <div className="image-actions">
                    <button className="btn btn-success btn-sm">
                      ▶️ Run
                    </button>
                    <button 
                      className="btn btn-danger btn-sm" 
                      onClick={() => removeImage(image.RepoTags?.[0] || image.Id)}
                    >
                      🗑️ Remove
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Search Registry Tab */}
      {activeTab === 'search' && (
        <div className="registry-tab">
          <div className="tab-header">
            <h2>🔍 Search Docker Hub</h2>
            {!isDockerLoggedIn && (
              <div className="search-warning">
                <span>⚠️ Login required for full search functionality</span>
              </div>
            )}
          </div>

          <div className="search-form">
            <div className="form-group">
              <div className="search-input-group">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="e.g., nginx, postgres, python, redis"
                  className="form-input"
                  onKeyPress={(e) => e.key === 'Enter' && searchRegistry()}
                />
                <button 
                  className="btn btn-primary" 
                  onClick={searchRegistry} 
                  disabled={loading || !searchQuery.trim()}
                >
                  <span className="btn-icon">🔍</span>
                  <span className="btn-text">Search</span>
                </button>
              </div>
            </div>
          </div>

          {loading ? (
            <div className="loading-state">
              <div className="loading-spinner"></div>
              <p>Searching Docker Hub...</p>
            </div>
          ) : searchResults.length > 0 ? (
            <div className="search-results">
              <h3>Search Results ({searchResults.length})</h3>
              <div className="results-grid">
                {searchResults.map((result, index) => (
                  <div key={index} className="search-result-card">
                    <div className="result-header">
                      <div className="result-name">{result.name}</div>
                      <div className="result-official">
                        {result.is_official && <span className="official-badge">✅ Official</span>}
                      </div>
                    </div>
                    <div className="result-description">
                      {result.description || 'No description available'}
                    </div>
                    <div className="result-stats">
                      <span className="stat">⭐ {result.star_count || 0}</span>
                      <span className="stat">⬇️ {result.pull_count || 0}</span>
                    </div>
                    <div className="result-actions">
                      <button 
                        className="btn btn-success btn-sm"
                        onClick={() => {
                          setPullImageName(result.name);
                          setActiveTab('manage');
                        }}
                      >
                        ⬇️ Pull
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : searchQuery ? (
            <div className="empty-state">
              <div className="empty-icon">🔍</div>
              <h3>No Results Found</h3>
              <p>Try a different search term.</p>
            </div>
          ) : (
            <div className="empty-state">
              <div className="empty-icon">🔍</div>
              <h3>Search Docker Hub</h3>
              <p>Enter a search query to find container images.</p>
            </div>
          )}
        </div>
      )}

      {/* Pull Image Tab */}
      {activeTab === 'manage' && (
        <div className="registry-tab">
          <div className="tab-header">
            <h2>⬇️ Pull Image</h2>
          </div>

          <div className="pull-form">
            <div className="form-group">
              <label>Image Name</label>
              <div className="input-group">
                <input
                  type="text"
                  value={pullImageName}
                  onChange={(e) => setPullImageName(e.target.value)}
                  placeholder="e.g., nginx:latest, postgres:15, python:3.11-alpine"
                  className="form-input"
                  onKeyPress={(e) => e.key === 'Enter' && pullImage()}
                />
                <button 
                  className="btn btn-success" 
                  onClick={pullImage} 
                  disabled={loading || !pullImageName.trim()}
                >
                  <span className="btn-icon">⬇️</span>
                  <span className="btn-text">Pull Image</span>
                </button>
              </div>
              <div className="form-hint">
                💡 Examples: nginx, postgres:15, python:3.11, redis:alpine
              </div>
            </div>

            <div className="popular-images">
              <h4>🚀 Popular Images</h4>
              <div className="popular-grid">
                {['nginx:latest', 'postgres:15', 'redis:alpine', 'python:3.11', 'node:18', 'mysql:8.0'].map((image) => (
                  <button
                    key={image}
                    className="popular-image-btn"
                    onClick={() => setPullImageName(image)}
                  >
                    {image}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ImageRegistry;