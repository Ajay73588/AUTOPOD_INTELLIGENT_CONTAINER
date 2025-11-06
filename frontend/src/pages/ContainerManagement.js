import React, { useState, useEffect } from "react";
import {
  apiService,
  checkBackendConnection,
  testContainerAction,
} from "../services/api";
import ContainerGrid from "../components/ContainerGrid";
import ContainerActions from "../components/ContainerActions";
import "../styles/ContainerManagement.css";

const ContainerManagement = () => {
  const [containers, setContainers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedContainer, setSelectedContainer] = useState(null);
  const [actionStatus, setActionStatus] = useState("");
  const [loadingActions, setLoadingActions] = useState({});
  const [deployUrl, setDeployUrl] = useState("");
  const [isDeploying, setIsDeploying] = useState(false);
  const [showDeploySection, setShowDeploySection] = useState(false);
  const [showPushSection, setShowPushSection] = useState(false);
  const [dockerUsername, setDockerUsername] = useState("");
  const [dockerPassword, setDockerPassword] = useState("");
  const [isDockerLoggedIn, setIsDockerLoggedIn] = useState(false);
  const [checkingLogin, setCheckingLogin] = useState(false);
  const [showLoginForm, setShowLoginForm] = useState(false);

  useEffect(() => {
    fetchContainers();
    const interval = setInterval(fetchContainers, 5000);
    testBackendConnection();
    return () => clearInterval(interval);
    
  }, []);

  const fetchContainers = async () => {
    try {
      console.log("🔄 Fetching containers...");
      const response = await apiService.getContainers();
      console.log("📦 Containers response:", response.data);

      if (response.data.success) {
        setContainers(response.data.data || []);

        // Keep the selected container updated if it exists
        if (selectedContainer) {
          const updatedContainer = (response.data.data || []).find(
            (container) => container.Names?.[0] === selectedContainer.Names?.[0]
          );
          if (updatedContainer) {
            setSelectedContainer(updatedContainer);
          }
        }
      } else {
        console.error("❌ Failed to fetch containers:", response.data.error);
      }
    } catch (error) {
      console.error("💥 Error fetching containers:", error);
      setActionStatus(`❌ Error fetching containers: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const setActionLoading = (containerName, action, isLoading) => {
    setLoadingActions((prev) => ({
      ...prev,
      [`${containerName}_${action}`]: isLoading,
    }));
  };

  // Function to check container state
  const checkContainerState = (container) => {
    const status = container.Status || container.status || '';
    const state = container.State || container.state || '';
    
    console.log('🔍 Container status:', status);
    console.log('🔍 Container state:', state);
    
    if (status.toLowerCase().includes('exited') || state.toLowerCase() === 'exited') {
      return 'exited';
    } else if (status.toLowerCase().includes('running') || state.toLowerCase() === 'running') {
      return 'running';
    } else if (status.toLowerCase().includes('created') || state.toLowerCase() === 'created') {
      return 'created';
    } else {
      return 'unknown';
    }
  };

  // Function to get exact container name
  const getExactContainerName = (container) => {
    // Try different possible name fields
    return container.Names?.[0] || 
           container.container_name || 
           container.Name || 
           'Unknown Container';
  };

  const testBackendConnection = async () => {
    try {
      console.log("🔗 Testing backend connection...");
      const response = await apiService.healthCheck();
      console.log("✅ Backend connection successful:", response.data);
      
      const containersResponse = await apiService.getContainers();
      console.log("📦 Raw containers response:", containersResponse.data);
    } catch (error) {
      console.error("❌ Backend connection failed:", error);
    }
  };

  const handleContainerAction = async (action, containerName) => {
    console.log(`🔄 Attempting to ${action} container:`, containerName);
    console.log("📋 All containers:", containers);

    // Find the container object
    const containerObj = containers.find(
      (container) =>
        container.Names?.[0] === containerName ||
        container.container_name === containerName
    );
    
    if (!containerObj) {
      setActionStatus(`❌ Container ${containerName} not found`);
      return;
    }
    
    const exactName = getExactContainerName(containerObj);
    const containerState = checkContainerState(containerObj);
    console.log(`🔍 Container ${exactName} state:`, containerState);

    try {
      setActionLoading(exactName, action, true);
      setActionStatus(`${action}ing container ${exactName}...`);

      let response;
      switch (action) {
        case "start":
          if (containerState === 'running') {
            setActionStatus('⚠️ Container is already running');
            setActionLoading(exactName, action, false);
            return;
          }
          console.log("📤 Sending start request...");
          response = await apiService.startContainer(exactName);
          break;
        case "stop":
          if (containerState !== 'running') {
            setActionStatus('⚠️ Container is not running');
            setActionLoading(exactName, action, false);
            return;
          }
          console.log("📤 Sending stop request...");
          response = await apiService.stopContainer(exactName);
          break;
        case "restart":
          console.log("📤 Sending restart request...");
          response = await apiService.restartContainer(exactName);
          break;
        case "remove":
          console.log("📤 Sending remove request...");
          if (
            !window.confirm(
              `Are you sure you want to remove container ${exactName}? This action cannot be undone.`
            )
          ) {
            setActionStatus("");
            setActionLoading(exactName, action, false);
            return;
          }
          response = await apiService.removeContainer(exactName);
          // Clear selection if the removed container was selected
          if (
            selectedContainer &&
            (selectedContainer.Names?.[0] === exactName ||
              selectedContainer.container_name === exactName)
          ) {
            setSelectedContainer(null);
          }
          break;
        default:
          setActionLoading(exactName, action, false);
          return;
      }

      console.log("📥 Action response:", response);
      console.log("📥 Response data:", response.data);

      if (response.data.success) {
        setActionStatus(
          `✅ Container ${exactName} ${action}ed successfully`
        );
        // Refresh containers after action
        setTimeout(fetchContainers, 1000);
      } else {
        setActionStatus(
          `❌ Failed to ${action} container: ${response.data.error}`
        );
      }
    } catch (error) {
      console.error(`💥 Error ${action} container:`, error);
      console.error("Error response:", error.response);
      console.error("Error message:", error.message);

      let errorMessage = `❌ Error ${action}ing container: `;
      if (error.response?.data?.error) {
        errorMessage += error.response.data.error;
      } else if (error.message) {
        errorMessage += error.message;
      } else {
        errorMessage += "Unknown error occurred";
      }

      setActionStatus(errorMessage);
    } finally {
      setActionLoading(exactName, action, false);
    }
  };

  const handleDeploy = async () => {
    if (!deployUrl.trim()) {
      setActionStatus("❌ Please enter a GitHub repository URL");
      return;
    }

    try {
      setIsDeploying(true);
      setActionStatus("🚀 Starting deployment...");

      // Send webhook payload to trigger deployment
      const payload = {
        repository: {
          clone_url: deployUrl.trim(),
          name: extractRepoName(deployUrl.trim()),
        },
      };

      const response = await apiService.triggerWebhook(payload);

      if (response.data.status === "success") {
        setActionStatus(`✅ ${response.data.message}`);
        setDeployUrl("");
        setShowDeploySection(false);
        // Refresh containers after deployment
        setTimeout(fetchContainers, 3000);
      } else {
        setActionStatus(`❌ Deployment failed: ${response.data.message}`);
      }
    } catch (error) {
      console.error("Error deploying repository:", error);
      setActionStatus(
        `❌ Deployment error: ${error.response?.data?.message || error.message}`
      );
    } finally {
      setIsDeploying(false);
    }
  };

  const extractRepoName = (url) => {
    try {
      const match = url.match(/github\.com\/([^\/]+\/[^\/]+)/);
      return match
        ? match[1].split("/").pop().replace(".git", "")
        : "webhook-app";
    } catch {
      return "webhook-app";
    }
  };

  // Docker Login Functions
  const handleDockerLogin = async () => {
    if (!dockerUsername || !dockerPassword) {
      setActionStatus("❌ Please enter both username and password");
      return;
    }

    try {
      setCheckingLogin(true);
      setActionStatus("🔐 Logging in to Docker Hub...");

      const response = await apiService.dockerLogin({
        username: dockerUsername,
        password: dockerPassword,
        registry: "docker.io"
      });

      if (response.data.success) {
        setIsDockerLoggedIn(true);
        setActionStatus("✅ Successfully logged in to Docker Hub!");
        setShowLoginForm(false);
        setDockerPassword(""); // Clear password for security
      } else {
        setActionStatus(`❌ Login failed: ${response.data.error}`);
        setIsDockerLoggedIn(false);
      }
    } catch (error) {
      console.error('Error logging in to Docker:', error);
      setActionStatus(`❌ Login error: ${error.response?.data?.error || error.message}`);
      setIsDockerLoggedIn(false);
    } finally {
      setCheckingLogin(false);
    }
  };

  const handleDockerLogout = async () => {
    try {
      setActionStatus("🔐 Logging out from Docker Hub...");
      const response = await apiService.dockerLogout();
      
      if (response.data.success) {
        setIsDockerLoggedIn(false);
        setActionStatus("✅ Successfully logged out from Docker Hub!");
        setDockerUsername("");
        setDockerPassword("");
      }
    } catch (error) {
      console.error('Error logging out from Docker:', error);
      setActionStatus(`❌ Logout error: ${error.response?.data?.error || error.message}`);
    }
  };

  // Check Docker login status
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

  // Helper function to extract image name from container
  const getImageNameFromContainer = (container) => {
    // Try different possible image fields
    const image = container.Image || container.image;
    
    if (!image) {
      return null;
    }

    // Handle different image formats:
    // 1. "nginx:latest" -> "nginx"
    // 2. "docker.io/nginx:latest" -> "nginx" 
    // 3. "localhost/autopod-cpython:latest" -> "autopod-cpython"
    
    let cleanImageName = image;
    
    // Remove registry prefix
    if (cleanImageName.includes('/')) {
      cleanImageName = cleanImageName.split('/').pop();
    }
    
    // Remove tag
    if (cleanImageName.includes(':')) {
      cleanImageName = cleanImageName.split(':')[0];
    }
    
    return cleanImageName;
  };

  const handlePushToDocker = async () => {
    if (!selectedContainer) {
      setActionStatus('❌ Please select a container first');
      return;
    }

    if (!dockerUsername) {
      setActionStatus('❌ Please enter your Docker Hub username');
      return;
    }

    try {
      // Get the image name from the selected container
      const imageName = getImageNameFromContainer(selectedContainer);
      
      if (!imageName) {
        setActionStatus('❌ Could not find image name for selected container');
        return;
      }

      setActionStatus(`🚀 Pushing image ${imageName} to Docker Hub...`);
      
      const response = await apiService.pushImage({
        image_name: imageName,
        registry: 'docker.io',
        username: dockerUsername
      });

      if (response.data.success) {
        const { tagged_name, registry_url, pull_command } = response.data.data;
        setActionStatus(`✅ Image pushed successfully!`);
        
        // Show success details
        setTimeout(() => {
          setActionStatus(`
            ✅ Push Successful!
            📦 Image: ${tagged_name}
            🌐 URL: ${registry_url}
            📥 Pull: ${pull_command}
          `);
        }, 1000);
        
        // Close push section after success
        setTimeout(() => {
          setShowPushSection(false);
        }, 5000);
      } else {
        setActionStatus(`❌ Push failed: ${response.data.error}`);
      }
    } catch (error) {
      console.error('Error pushing image:', error);
      setActionStatus(`❌ Push error: ${error.response?.data?.error || error.message}`);
    }
  };

  const openPushSection = async () => {
    if (!selectedContainer) {
      setActionStatus('❌ Please select a container first to push its image');
      return;
    }
    
    setShowPushSection(true);
    await checkDockerLoginStatus();
  };

  // Debug function to test backend connection and container actions
  const debugContainerActions = async () => {
    try {
      setActionStatus("🔍 Testing backend connection...");

      // Check backend connection
      const connection = await checkBackendConnection();
      console.log("🔗 Backend connection:", connection);

      if (!connection.connected) {
        setActionStatus(
          "❌ Backend is not connected! Check if Flask is running on port 5000."
        );
        return;
      }

      setActionStatus("✅ Backend connected! Testing container actions...");

      // Get containers to see what's available
      const containersResponse = await apiService.getContainers();
      console.log("📦 Available containers:", containersResponse.data);

      if (
        containersResponse.data.success &&
        containersResponse.data.data.length > 0
      ) {
        const firstContainer = containersResponse.data.data[0];
        const containerName = getExactContainerName(firstContainer);

        setActionStatus(`🧪 Testing actions on container: ${containerName}`);

        // Test start action
        await testContainerAction("start", containerName);
        setActionStatus("✅ Container action test completed!");
      } else {
        setActionStatus("ℹ️ No containers available to test");
      }
    } catch (error) {
      console.error("🧪 Debug test failed:", error);
      setActionStatus(`❌ Debug test failed: ${error.message}`);
    }
  };

  if (loading) {
    return <div className="loading">Loading containers...</div>;
  }

  return (
    <div className="container-management">
      <div className="page-header">
        <h1>Container Management</h1>
        <p>Monitor and manage your Podman containers</p>

        <div className="header-actions">
          <button
            onClick={() => setShowDeploySection(!showDeploySection)}
            className="deploy-toggle-button"
          >
            {showDeploySection ? "❌ Cancel" : "🚀 Deploy New"}
          </button>

          {/* Push to Docker Button */}
          <button 
            onClick={openPushSection}
            className="push-toggle-button"
            title="Push image to Docker Hub"
          >
            📤 Push to Docker
          </button>

          {/* Debug button */}
          <button
            onClick={debugContainerActions}
            className="debug-button"
            title="Test container actions and backend connection"
          >
            🐛 Debug
          </button>
        </div>
      </div>

      {actionStatus && (
        <div
          className={`status-message ${
            actionStatus.includes("✅")
              ? "success"
              : actionStatus.includes("🚀")
              ? "info"
              : actionStatus.includes("🔍")
              ? "info"
              : actionStatus.includes("🧪")
              ? "warning"
              : actionStatus.includes("ℹ️")
              ? "info"
              : "error"
          }`}
        >
          {actionStatus}
        </div>
      )}

      {showDeploySection && (
        <div className="deploy-section">
          <div className="deploy-card">
            <h3>🚀 Deploy from GitHub</h3>
            <p>Enter a GitHub repository URL to build and deploy a container</p>

            <div className="deploy-input-group">
              <input
                type="text"
                placeholder="https://github.com/username/repository"
                value={deployUrl}
                onChange={(e) => setDeployUrl(e.target.value)}
                className="deploy-input"
                disabled={isDeploying}
              />
              <button
                onClick={handleDeploy}
                disabled={isDeploying || !deployUrl.trim()}
                className={`deploy-button ${isDeploying ? "loading" : ""}`}
              >
                {isDeploying ? "🔄 Deploying..." : "🚀 Deploy"}
              </button>
            </div>

            <div className="deploy-tips">
              <h4>💡 Deployment Tips:</h4>
              <ul>
                <li>
                  Repository should have a <code>Dockerfile</code> or{" "}
                  <code>Containerfile</code>
                </li>
                <li>
                  If no container file is found, a demo app will be deployed
                </li>
                <li>Container will be automatically built and started</li>
                <li>Port 80 will be exposed on a random available port</li>
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Push to Docker Section */}
      {showPushSection && (
        <div className="push-section">
          <div className="push-card">
            <div className="push-header">
              <h3>🚀 Push to Docker Hub</h3>
              <button 
                onClick={() => setShowPushSection(false)}
                className="close-btn"
              >
                ❌
              </button>
            </div>
            
            <div className="push-content">
              {/* Selected Container Info */}
              {selectedContainer && (
                <div className="selected-container-info">
                  <h4>Selected Container:</h4>
                  <div className="container-details">
                    <div className="detail-item">
                      <span>Container Name:</span>
                      <span>{selectedContainer.Names?.[0] || selectedContainer.container_name}</span>
                    </div>
                    <div className="detail-item">
                      <span>Image:</span>
                      <span>{selectedContainer.Image || selectedContainer.image}</span>
                    </div>
                    <div className="detail-item">
                      <span>Clean Image Name:</span>
                      <span className="image-name">{getImageNameFromContainer(selectedContainer)}</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Docker Login Status */}
              <div className={`login-status ${isDockerLoggedIn ? 'logged-in' : 'not-logged-in'}`}>
                {checkingLogin ? (
                  <span>🔍 Checking Docker Hub login status...</span>
                ) : isDockerLoggedIn ? (
                  <div className="login-status-info">
                    <span>✅ Logged in as: {dockerUsername}</span>
                    <button 
                      onClick={handleDockerLogout}
                      className="logout-btn"
                      title="Logout from Docker Hub"
                    >
                      🚪 Logout
                    </button>
                  </div>
                ) : (
                  <span>❌ Not logged in to Docker Hub</span>
                )}
              </div>

              {!isDockerLoggedIn && !showLoginForm && (
                <div className="login-prompt">
                  <p>You need to login to Docker Hub to push images</p>
                  <button 
                    onClick={() => setShowLoginForm(true)}
                    className="btn btn-primary"
                  >
                    🔐 Login to Docker Hub
                  </button>
                </div>
              )}

              {!isDockerLoggedIn && showLoginForm && (
                <div className="login-form">
                  <h4>🔐 Docker Hub Login</h4>
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
                      disabled={!dockerUsername || !dockerPassword || checkingLogin}
                      className="btn btn-primary"
                    >
                      {checkingLogin ? "🔄 Logging in..." : "🔐 Login"}
                    </button>
                    <button 
                      onClick={() => setShowLoginForm(false)}
                      className="btn btn-secondary"
                    >
                      Cancel
                    </button>
                  </div>
                  <div className="login-note">
                    <p>💡 Your credentials are sent securely to the backend and stored in environment variables.</p>
                  </div>
                </div>
              )}

              {isDockerLoggedIn && selectedContainer && (
                <div className="push-form">
                  <div className="form-group">
                    <label>Docker Hub Username:</label>
                    <input
                      type="text"
                      value={dockerUsername}
                      onChange={(e) => setDockerUsername(e.target.value)}
                      className="form-input"
                      placeholder="your-dockerhub-username"
                    />
                    <div className="form-hint">
                      Your image will be pushed as: docker.io/{dockerUsername || 'username'}/{getImageNameFromContainer(selectedContainer) || 'imagename'}:latest
                    </div>
                  </div>
                  
                  <div className="push-actions">
                    <button 
                      onClick={handlePushToDocker}
                      disabled={!dockerUsername}
                      className="btn btn-primary push-btn"
                    >
                      🚀 Push to Docker Hub
                    </button>
                    <button 
                      onClick={() => setShowPushSection(false)}
                      className="btn btn-secondary"
                    >
                      Cancel
                    </button>
                  </div>
                  
                  <div className="push-info">
                    <h4>📋 After Push:</h4>
                    <ul>
                      <li>Your image will be available at: <strong>https://hub.docker.com/r/{dockerUsername}/{getImageNameFromContainer(selectedContainer)}</strong></li>
                      <li>Others can pull it with: <code>podman pull {dockerUsername}/{getImageNameFromContainer(selectedContainer)}:latest</code></li>
                      <li>Make sure your repository is set to "Public" on Docker Hub for others to access</li>
                    </ul>
                  </div>
                </div>
              )}

              {isDockerLoggedIn && !selectedContainer && (
                <div className="no-selection">
                  <p>❌ Please select a container first to push its image.</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      <div className="management-layout">
        <div className="containers-section">
          <div className="section-header">
            <h2>📦 All Containers ({containers.length})</h2>
            <div className="section-actions">
              <button onClick={fetchContainers} className="refresh-button">
                🔄 Refresh
              </button>
            </div>
          </div>

          <ContainerGrid
            containers={containers}
            showActions={true}
            onContainerAction={handleContainerAction}
            onContainerSelect={setSelectedContainer}
            selectedContainer={selectedContainer}
            loadingActions={loadingActions}
          />
        </div>

        {selectedContainer && (
          <div className="details-section">
            <ContainerActions
              container={selectedContainer}
              onAction={handleContainerAction}
              loadingActions={loadingActions}
            />
          </div>
        )}
      </div>
    </div>
  );
};

export default ContainerManagement;