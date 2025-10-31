import React, { useState } from 'react';
import { apiService } from '../services/api';

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
          name: appName || 'auto-deployed-app'
        },
        after: "auto-deploy-" + Date.now()
      };

      console.log('Sending deployment request:', deploymentData);

      // Update progress
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
        
        // Refresh the page after 5 seconds to show new container
        setTimeout(() => {
          window.location.reload();
        }, 5000);
      } else {
        setStatusMessage(`❌ Deployment failed: ${response.data?.message || 'Unknown error'}`);
        setDeploymentProgress('Deployment failed');
      }
    } catch (error) {
      console.error('Deployment error details:', error);
      
      if (error.code === 'ECONNABORTED') {
        setStatusMessage('⏳ Deployment is taking longer than expected. Please check the backend logs for progress.');
        setDeploymentProgress('Operation in progress... This may take a few minutes for large repositories.');
        
        // Don't clear the form - let user check backend and try again
      } else if (error.response) {
        setStatusMessage(`❌ Server error: ${error.response.data?.message || error.response.statusText}`);
        setDeploymentProgress('Server returned an error');
      } else if (error.request) {
        setStatusMessage('❌ No response from server. Check if backend is running on port 5000.');
        setDeploymentProgress('Connection failed');
      } else {
        setStatusMessage(`❌ Deployment error: ${error.message}`);
        setDeploymentProgress('Unexpected error occurred');
      }
    } finally {
      setDeploying(false);
    }
  };

  const triggerSampleDeployment = async () => {
    // Use a smaller, faster repository for testing
    setGithubUrl('https://github.com/nginx/nginx.git');
    setAppName('nginx-demo');
    
    // Auto-trigger deployment after setting values
    setTimeout(() => {
      triggerDeployment();
    }, 100);
  };

  const getRepoNameFromUrl = (url) => {
    try {
      const match = url.match(/github\.com\/([^\/]+\/[^\/]+?)(?:\.git)?$/);
      return match ? match[1].replace('/', '-') : 'github-app';
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
    // Note: This won't cancel the backend process, just the frontend state
    setDeploying(false);
    setStatusMessage('⏹️ Deployment cancelled on frontend (backend may still be processing)');
    setDeploymentProgress('');
  };

  return (
    <section className="section">
      <div className="section-header">
        <h2>🌐 Deploy from GitHub</h2>
        <p className="section-subtitle">Automatically deploy containers from repositories</p>
      </div>
      
      <div className="deployment-form">
        <div className="form-group">
          <label htmlFor="github-url">Repository URL</label>
          <input
            type="text"
            id="github-url"
            value={githubUrl}
            onChange={(e) => handleUrlChange(e.target.value)}
            className="form-input"
            placeholder="https://github.com/username/repository.git"
            disabled={deploying}
          />
          <div className="form-hint">Enter any public GitHub repository URL with a Dockerfile</div>
        </div>

        <div className="form-group">
          <label htmlFor="app-name">Application Name</label>
          <input
            type="text"
            id="app-name"
            value={appName}
            onChange={(e) => setAppName(e.target.value)}
            className="form-input"
            placeholder="my-app"
            disabled={deploying}
          />
          <div className="form-hint">Auto-filled from repository name if left empty</div>
        </div>

        <div className="actions-grid">
          <button 
            className="btn btn-success" 
            onClick={triggerDeployment}
            disabled={deploying || !githubUrl}
          >
            <span className="btn-icon">
              {deploying ? '⏳' : '🚀'}
            </span>
            <span className="btn-text">
              {deploying ? 'Deploying...' : 'Deploy from GitHub'}
            </span>
          </button>
          
          <button 
            className="btn btn-secondary" 
            onClick={triggerSampleDeployment}
            disabled={deploying}
          >
            <span className="btn-icon">🧪</span>
            <span className="btn-text">Use Sample & Deploy</span>
          </button>

          {deploying && (
            <button 
              className="btn btn-warning" 
              onClick={cancelDeployment}
            >
              <span className="btn-icon">⏹️</span>
              <span className="btn-text">Cancel</span>
            </button>
          )}
        </div>

        {/* Progress and Status Messages */}
        {deploymentProgress && (
          <div className="progress-message">
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

        <div className="deployment-tips">
          <h4>💡 Deployment Information:</h4>
          <ul>
            <li>Deployments can take 2-5 minutes for the first time</li>
            <li>Large repositories may take longer to clone and build</li>
            <li>Check Flask backend terminal for real-time progress</li>
            <li>Make sure Podman is running on your system</li>
            <li>Git must be installed for repository cloning</li>
          </ul>
        </div>
      </div>
    </section>
  );
};

export default DeploymentSection;