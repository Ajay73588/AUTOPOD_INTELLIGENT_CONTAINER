import React, { useState } from 'react';
import { apiService } from '../services/api';
import '../styles/DeploymentSection.css';

const DeploymentSection = () => {
  const [githubUrl, setGithubUrl] = useState('');
  const [appName, setAppName] = useState('');
  const [statusMessage, setStatusMessage] = useState('');
  const [deploying, setDeploying] = useState(false);
  const [deploymentProgress, setDeploymentProgress] = useState('');

  const triggerDeployment = async () => {
    if (!githubUrl) {
      setStatusMessage('❌ Please enter a GitHub repository URL');
      return;
    }

    try {
      setDeploying(true);
      setStatusMessage('🚀 Starting deployment process...');
      setDeploymentProgress('Initializing deployment...');

      const deploymentData = {
        repository: {
          clone_url: githubUrl,
          name: appName || getRepoNameFromUrl(githubUrl)
        }
      };

      console.log('Sending deployment request:', deploymentData);
      setDeploymentProgress('Sending request to server...');

      const response = await apiService.triggerWebhook(deploymentData);

      console.log('Deployment response received:', response);

      if (response.data && response.data.status === 'success') {
        const successMessage = response.data.message || 'Deployment completed successfully!';
        setStatusMessage(`✅ ${successMessage}`);
        setDeploymentProgress('Deployment completed!');
        
        if (response.data.data) {
          const { container_name, port, access_url } = response.data.data;
          setDeploymentProgress(`Container: ${container_name} | Port: ${port} | URL: ${access_url}`);
        }
        
        setGithubUrl('');
        setAppName('');
        
      } else {
        const errorMsg = response.data?.message || 'Unknown error occurred';
        setStatusMessage(`❌ Deployment failed: ${errorMsg}`);
        setDeploymentProgress('Deployment failed - check backend logs');
      }
    } catch (error) {
      console.error('Deployment error details:', error);
      
      if (error.code === 'ECONNABORTED') {
        setStatusMessage('⏳ Deployment is taking longer than expected. The operation is running in background.');
        setDeploymentProgress('Building container image... This may take several minutes.');
      } else if (error.response) {
        const serverError = error.response.data?.message || error.response.statusText;
        setStatusMessage(`❌ Server error: ${serverError}`);
        setDeploymentProgress('Server returned an error');
      } else if (error.request) {
        setStatusMessage('❌ No response from server. Check if backend is running on port 5000.');
        setDeploymentProgress('Connection failed - backend might be down');
      } else {
        setStatusMessage(`❌ Deployment error: ${error.message}`);
        setDeploymentProgress('Unexpected error occurred');
      }
    } finally {
      setDeploying(false);
    }
  };

  const triggerSampleDeployment = (sampleUrl, sampleName) => {
    setGithubUrl(sampleUrl);
    setAppName(sampleName);
    
    // Auto-trigger deployment after setting values
    setTimeout(() => {
      triggerDeployment();
    }, 500);
  };

  const getRepoNameFromUrl = (url) => {
    try {
      const match = url.match(/github\.com\/([^\/]+\/[^\/]+?)(?:\.git)?$/);
      return match ? match[1].split('/').pop().replace('.git', '') : 'github-app';
    } catch {
      return 'github-app';
    }
  };

  const handleUrlChange = (url) => {
    setGithubUrl(url);
    if (url && !appName) {
      setAppName(getRepoNameFromUrl(url));
    }
  };

  const cancelDeployment = () => {
    setDeploying(false);
    setStatusMessage('⏹️ Deployment cancelled');
    setDeploymentProgress('');
  };

  const sampleRepositories = [
    {
      name: 'Simple Nginx',
      url: 'https://github.com/nginx/nginx',
      description: 'Basic Nginx web server'
    },
    {
      name: 'Node.js Demo',
      url: 'https://github.com/nodejs/docker-node',
      description: 'Official Node.js Docker sample'
    },
    {
      name: 'React App',
      url: 'https://github.com/facebook/create-react-app',
      description: 'Create React App template'
    }
  ];

  return (
    <section className="section">
      <div className="section-header">
        <h2>🚀 Quick Deploy</h2>
        <p className="section-subtitle">Deploy containers directly from GitHub repositories</p>
      </div>
      
      <div className="deployment-card">
        <div className="deployment-form">
          <div className="form-row">
            <div className="form-group">
              <label htmlFor="github-url">GitHub Repository URL</label>
              <input
                type="text"
                id="github-url"
                value={githubUrl}
                onChange={(e) => handleUrlChange(e.target.value)}
                className="form-input"
                placeholder="https://github.com/username/repository"
                disabled={deploying}
              />
            </div>

            <div className="form-group">
              <label htmlFor="app-name">Container Name</label>
              <input
                type="text"
                id="app-name"
                value={appName}
                onChange={(e) => setAppName(e.target.value)}
                className="form-input"
                placeholder="my-app"
                disabled={deploying}
              />
            </div>
          </div>

          <div className="deploy-actions">
            <button 
              className={`btn btn-primary deploy-btn ${deploying ? 'loading' : ''}`}
              onClick={triggerDeployment}
              disabled={deploying || !githubUrl}
            >
              <span className="btn-icon">
                {deploying ? '🔄' : '🚀'}
              </span>
              {deploying ? 'Deploying...' : 'Deploy Now'}
            </button>
            
            {deploying && (
              <button 
                className="btn btn-secondary cancel-btn"
                onClick={cancelDeployment}
              >
                <span className="btn-icon">⏹️</span>
                Cancel
              </button>
            )}
          </div>

          {/* Progress and Status Messages */}
          {deploymentProgress && (
            <div className="progress-container">
              <div className="progress-text">{deploymentProgress}</div>
              {deploying && (
                <div className="progress-bar">
                  <div className="progress-fill"></div>
                </div>
              )}
            </div>
          )}

          {statusMessage && (
            <div className={`status-message ${
              statusMessage.includes('✅') ? 'success' : 
              statusMessage.includes('🚀') ? 'info' : 
              statusMessage.includes('⏳') ? 'warning' : 
              'error'
            }`}>
              {statusMessage}
            </div>
          )}
        </div>

        {/* Sample Repositories */}
        <div className="sample-repositories">
          <h4>🎯 Try Sample Repositories</h4>
          <div className="sample-grid">
            {sampleRepositories.map((repo, index) => (
              <div key={index} className="sample-card">
                <h5>{repo.name}</h5>
                <p>{repo.description}</p>
                <button 
                  className="btn btn-outline sample-btn"
                  onClick={() => triggerSampleDeployment(repo.url, repo.name.toLowerCase())}
                  disabled={deploying}
                >
                  Deploy {repo.name}
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Deployment Information */}
        <div className="deployment-info">
          <div className="info-section">
            <h5>💡 How it works</h5>
            <ul>
              <li>Paste any public GitHub repository URL</li>
              <li>Auto-detects Dockerfile or Containerfile</li>
              <li>Builds container image automatically</li>
              <li>Deploys container with auto-port mapping</li>
              <li>Appears in your containers list instantly</li>
            </ul>
          </div>

          <div className="info-section">
            <h5>⚡ Quick Tips</h5>
            <ul>
              <li>First deployment may take 2-3 minutes</li>
              <li>Check backend terminal for build progress</li>
              <li>No Dockerfile? We'll create a demo app</li>
              <li>Refresh containers list after deployment</li>
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
};

export default DeploymentSection;