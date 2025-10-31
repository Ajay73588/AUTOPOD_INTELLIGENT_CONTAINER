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

  useEffect(() => {
    if (activeTab === 'local') {
      fetchLocalImages();
    }
  }, [activeTab]);

  const fetchLocalImages = async () => {
    try {
      setLoading(true);
      const response = await apiService.getImages();
      if (response.data.success) {
        setLocalImages(response.data.data || []);
      }
    } catch (error) {
      console.error('Error fetching local images:', error);
      setStatusMessage('Error fetching local images');
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
      setStatusMessage('Error searching registry');
    } finally {
      setLoading(false);
    }
  };

  const pullImage = async () => {
    if (!pullImageName.trim()) return;
    
    try {
      setStatusMessage(`Pulling image: ${pullImageName}...`);
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
      setStatusMessage('Error pulling image');
    }
  };

  const removeImage = async (imageName) => {
    if (!window.confirm(`Are you sure you want to remove image ${imageName}?`)) return;
    
    try {
      setStatusMessage(`Removing image: ${imageName}...`);
      const response = await apiService.removeImage(imageName);
      if (response.data.success) {
        setStatusMessage(`✅ Image removed successfully`);
        fetchLocalImages();
      } else {
        setStatusMessage(`❌ Failed to remove image: ${response.data.error}`);
      }
    } catch (error) {
      console.error('Error removing image:', error);
      setStatusMessage('Error removing image');
    }
  };

  return (
    <div className="image-registry">
      <div className="page-header">
        <h1>📦 Container Registry</h1>
        <p>Manage images, search registries, and pull/push containers</p>
      </div>

      {/* Tabs */}
      <div className="registry-tabs">
        <button 
          className={`tab-btn ${activeTab === 'local' ? 'active' : ''}`}
          onClick={() => setActiveTab('local')}
        >
          <span className="tab-icon">💾</span>
          <span className="tab-text">Local Images</span>
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
          <span className="tab-icon">⚙️</span>
          <span className="tab-text">Manage</span>
        </button>
      </div>

      {/* Status Message */}
      {statusMessage && (
        <div className={`status-message ${statusMessage.includes('✅') ? 'success' : statusMessage.includes('❌') ? 'error' : 'info'}`}>
          {statusMessage}
        </div>
      )}

      {/* Local Images Tab */}
      {activeTab === 'local' && (
        <div className="registry-tab active">
          <div className="tab-actions">
            <button className="btn btn-secondary" onClick={fetchLocalImages} disabled={loading}>
              <span className="btn-icon">🔄</span>
              <span className="btn-text">Refresh</span>
            </button>
          </div>

          {loading ? (
            <div className="loading">Loading local images...</div>
          ) : localImages.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">📦</div>
              <h3>No Local Images</h3>
              <p>Pull an image from the registry to get started.</p>
            </div>
          ) : (
            <div className="images-grid">
              {localImages.map((image, index) => (
                <div key={index} className="image-card">
                  <div className="image-header">
                    <div className="image-name">{image.RepoTags?.[0] || image.Id}</div>
                    <div className="image-size">{image.Size || 'N/A'}</div>
                  </div>
                  <div className="image-details">
                    <div className="detail-item">
                      <span>ID:</span>
                      <span>{image.Id?.substring(0, 12) || 'N/A'}</span>
                    </div>
                    <div className="detail-item">
                      <span>Created:</span>
                      <span>{image.Created ? new Date(image.Created * 1000).toLocaleDateString() : 'N/A'}</span>
                    </div>
                  </div>
                  <div className="image-actions">
                    <button className="btn btn-success btn-sm">
                      ▶️ Run
                    </button>
                    <button className="btn btn-danger btn-sm" onClick={() => removeImage(image.RepoTags?.[0])}>
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
          <div className="search-form">
            <div className="form-group">
              <label>Search Docker Hub</label>
              <div className="search-input-group">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="e.g., nginx, postgres, python"
                  className="form-input"
                />
                <button className="btn btn-primary" onClick={searchRegistry} disabled={loading}>
                  <span className="btn-icon">🔍</span>
                  <span className="btn-text">Search</span>
                </button>
              </div>
            </div>
          </div>

          {loading ? (
            <div className="loading">Searching registry...</div>
          ) : searchResults.length > 0 ? (
            <div className="search-results">
              {searchResults.map((result, index) => (
                <div key={index} className="search-result-card">
                  <div className="result-header">
                    <div className="result-name">{result.name}</div>
                  </div>
                  <div className="result-description">{result.description || 'No description available'}</div>
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
          ) : (
            <div className="empty-state">
              <div className="empty-icon">🔍</div>
              <h3>Search for Images</h3>
              <p>Enter a search query to find images in the registry.</p>
            </div>
          )}
        </div>
      )}

      {/* Manage Tab */}
      {activeTab === 'manage' && (
        <div className="registry-tab">
          <div className="manage-form">
            <div className="form-group">
              <label>Pull Image</label>
              <div className="input-group">
                <input
                  type="text"
                  value={pullImageName}
                  onChange={(e) => setPullImageName(e.target.value)}
                  placeholder="e.g., nginx:latest, postgres:15"
                  className="form-input"
                />
                <button className="btn btn-success" onClick={pullImage} disabled={loading}>
                  <span className="btn-icon">⬇️</span>
                  <span className="btn-text">Pull</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ImageRegistry;