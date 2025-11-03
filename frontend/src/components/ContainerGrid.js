import React from 'react';
import { Play, Square, RotateCcw, Trash2, ExternalLink, Loader, Bug } from 'lucide-react';
import '../styles/ContainerGrid.css';

const ContainerGrid = ({ 
  containers, 
  showActions = true, 
  onContainerAction,
  onContainerSelect,
  selectedContainer,
  loadingActions = {} // Track loading states for individual containers
}) => {
  
  const getStatusBadge = (status) => {
    const statusLower = status.toLowerCase();
    if (statusLower.includes('running') || statusLower.includes('up')) {
      return 'badge-running';
    } else if (statusLower.includes('exited') || statusLower.includes('stopped')) {
      return 'badge-stopped';
    } else if (statusLower.includes('created')) {
      return 'badge-created';
    } else if (statusLower.includes('paused')) {
      return 'badge-paused';
    } else {
      return 'badge-unknown';
    }
  };

  const getStatusText = (status) => {
    const statusLower = status.toLowerCase();
    if (statusLower.includes('running') || statusLower.includes('up')) {
      return 'Running';
    } else if (statusLower.includes('exited') || statusLower.includes('stopped')) {
      return 'Stopped';
    } else if (statusLower.includes('created')) {
      return 'Created';
    } else if (statusLower.includes('paused')) {
      return 'Paused';
    } else {
      return status;
    }
  };

  const formatDate = (dateString) => {
    try {
      if (typeof dateString === 'number') {
        return new Date(dateString * 1000).toLocaleString();
      }
      return new Date(dateString).toLocaleString();
    } catch {
      return 'Unknown';
    }
  };

  const handleAction = (action, containerName, container, e) => {
    e.stopPropagation();
    console.log(`🔄 ContainerGrid: ${action} action for container:`, {
      containerName,
      actualNames: container.Names,
      container_name: container.container_name,
      status: container.Status,
      state: container.State
    });
    
    if (onContainerAction) {
      onContainerAction(action, containerName);
    }
  };

  const handleContainerClick = (container) => {
    console.log('🔍 Container clicked:', {
      names: container.Names,
      container_name: container.container_name,
      status: container.Status,
      state: container.State
    });
    
    if (onContainerSelect) {
      onContainerSelect(container);
    }
  };

  const isActionLoading = (containerName, action) => {
    return loadingActions[`${containerName}_${action}`] || false;
  };

  // Function to get exact container name for display and actions
  const getExactContainerName = (container) => {
    // Try different possible name fields
    return container.Names?.[0] || 
           container.container_name || 
           container.Name || 
           'Unknown Container';
  };

  // Function to check if container is GitHub deployed
  const isGitHubContainer = (container) => {
    const name = getExactContainerName(container).toLowerCase();
    return name.includes('autopod') || name.includes('webhook') || name.includes('github');
  };

  // Debug function to log container details
  const debugContainer = (container, e) => {
    e.stopPropagation();
    const exactName = getExactContainerName(container);
    console.log('🐛 Container Debug Info:', {
      exactName,
      allNames: container.Names,
      container_name: container.container_name,
      status: container.Status,
      state: container.State,
      id: container.Id,
      image: container.Image,
      isGitHub: isGitHubContainer(container),
      ports: container.Ports
    });
    
    // Show alert with basic info
    alert(`Container Debug Info:\n\nName: ${exactName}\nStatus: ${container.Status}\nState: ${container.State}\nGitHub Container: ${isGitHubContainer(container) ? 'Yes' : 'No'}\n\nCheck browser console for full details.`);
  };

  if (!containers || containers.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-icon">📦</div>
        <h3>No Containers Found</h3>
        <p>No containers are currently running or available.</p>
      </div>
    );
  }

  return (
    <div className="containers-grid">
      {containers.map((container, index) => {
        const exactName = getExactContainerName(container);
        const containerId = container.Id || container.id || `container-${index}`;
        const status = container.Status || container.status || 'Unknown';
        const image = container.Image || container.image || 'N/A';
        const created = container.Created || container.created_at;
        const ports = container.Ports || [];
        const state = container.State || 'unknown';
        
        const isRunning = status.toLowerCase().includes('running') || state.toLowerCase() === 'running';
        const isStopped = status.toLowerCase().includes('exited') || 
                         status.toLowerCase().includes('stopped') || 
                         state.toLowerCase() === 'exited';
        const isCreated = status.toLowerCase().includes('created') || state.toLowerCase() === 'created';

        const isSelected = selectedContainer && 
          (selectedContainer.Names?.[0] === exactName || 
           selectedContainer.container_name === exactName);

        const isGitHub = isGitHubContainer(container);

        return (
          <div 
            key={containerId}
            className={`container-card ${isSelected ? 'selected' : ''} ${isGitHub ? 'github-container' : ''}`}
            onClick={() => handleContainerClick(container)}
          >
            <div className="container-header">
              <div className="container-name-section">
                <div className="container-icon">
                  {isGitHub ? '🚀' : '🐳'}
                </div>
                <div className="container-name-info">
                  <div className="container-name" title={exactName}>
                    {exactName}
                  </div>
                  {isGitHub && (
                    <div className="container-badge github-badge">
                      GitHub
                    </div>
                  )}
                </div>
              </div>
              <div className="header-right">
                <span className={`status-badge ${getStatusBadge(status)}`}>
                  {getStatusText(status)}
                </span>
                <button 
                  className="debug-btn"
                  onClick={(e) => debugContainer(container, e)}
                  title="Debug Container Info"
                >
                  <Bug size={12} />
                </button>
              </div>
            </div>

            <div className="container-details">
              <div className="detail-item">
                <span className="detail-label">Image:</span>
                <span className="detail-value image-name" title={image}>
                  {image.length > 30 ? `${image.substring(0, 30)}...` : image}
                </span>
              </div>
              
              <div className="detail-item">
                <span className="detail-label">Status:</span>
                <span className="detail-value">{status}</span>
              </div>

              <div className="detail-item">
                <span className="detail-label">State:</span>
                <span className="detail-value">{state}</span>
              </div>
              
              <div className="detail-item">
                <span className="detail-label">Created:</span>
                <span className="detail-value">{formatDate(created)}</span>
              </div>

              {ports.length > 0 && (
                <div className="detail-item">
                  <span className="detail-label">Ports:</span>
                  <span className="detail-value ports">
                    {ports.map((port, idx) => (
                      <span key={idx} className="port-mapping">
                        {port.PublicPort || port.HostPort || 'N/A'}:{port.PrivatePort || port.ContainerPort || 'N/A'}
                      </span>
                    ))}
                  </span>
                </div>
              )}

              {/* Debug info - visible on hover or always for GitHub containers */}
              <div className={`debug-info ${isGitHub ? 'always-visible' : ''}`}>
                <div className="debug-item">
                  <span className="debug-label">ID:</span>
                  <span className="debug-value">{containerId.substring(0, 12)}</span>
                </div>
                <div className="debug-item">
                  <span className="debug-label">All Names:</span>
                  <span className="debug-value">{JSON.stringify(container.Names)}</span>
                </div>
                <div className="debug-item">
                  <span className="debug-label">Container Name:</span>
                  <span className="debug-value">{container.container_name || 'N/A'}</span>
                </div>
              </div>
            </div>

            {showActions && (
              <div className="container-actions">
                {/* Start Button - Show for stopped/created containers */}
                {(isStopped || isCreated) && (
                  <button 
                    className="action-btn btn-success btn-sm"
                    onClick={(e) => handleAction('start', exactName, container, e)}
                    disabled={isActionLoading(exactName, 'start')}
                    title="Start Container"
                  >
                    {isActionLoading(exactName, 'start') ? (
                      <Loader size={14} className="spin" />
                    ) : (
                      <Play size={14} />
                    )}
                    <span>
                      {isActionLoading(exactName, 'start') ? 'Starting...' : 'Start'}
                    </span>
                  </button>
                )}
                
                {/* Stop Button - Show for running containers */}
                {isRunning && (
                  <button 
                    className="action-btn btn-warning btn-sm"
                    onClick={(e) => handleAction('stop', exactName, container, e)}
                    disabled={isActionLoading(exactName, 'stop')}
                    title="Stop Container"
                  >
                    {isActionLoading(exactName, 'stop') ? (
                      <Loader size={14} className="spin" />
                    ) : (
                      <Square size={14} />
                    )}
                    <span>
                      {isActionLoading(exactName, 'stop') ? 'Stopping...' : 'Stop'}
                    </span>
                  </button>
                )}
                
                {/* Restart Button - Show for running containers */}
                {isRunning && (
                  <button 
                    className="action-btn btn-secondary btn-sm"
                    onClick={(e) => handleAction('restart', exactName, container, e)}
                    disabled={isActionLoading(exactName, 'restart')}
                    title="Restart Container"
                  >
                    {isActionLoading(exactName, 'restart') ? (
                      <Loader size={14} className="spin" />
                    ) : (
                      <RotateCcw size={14} />
                    )}
                    <span>
                      {isActionLoading(exactName, 'restart') ? 'Restarting...' : 'Restart'}
                    </span>
                  </button>
                )}
                
                {/* Remove Button - Always show but warn if container is running */}
                <button 
                  className="action-btn btn-danger btn-sm"
                  onClick={(e) => handleAction('remove', exactName, container, e)}
                  disabled={isActionLoading(exactName, 'remove')}
                  title={isRunning ? "Remove Container (will stop first)" : "Remove Container"}
                >
                  {isActionLoading(exactName, 'remove') ? (
                    <Loader size={14} className="spin" />
                  ) : (
                    <Trash2 size={14} />
                  )}
                  <span>
                    {isActionLoading(exactName, 'remove') ? 'Removing...' : 'Remove'}
                  </span>
                </button>

                {/* Open Web Interface - Show for running containers with ports */}
                {isRunning && ports.length > 0 && (
                  <button 
                    className="action-btn btn-primary btn-sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      // Open the first available port
                      const port = ports[0];
                      const hostPort = port.PublicPort || port.HostPort;
                      if (hostPort) {
                        const url = `http://localhost:${hostPort}`;
                        console.log(`🌐 Opening web interface: ${url}`);
                        window.open(url, '_blank');
                      }
                    }}
                    title="Open Web Interface"
                  >
                    <ExternalLink size={14} />
                    <span>Open</span>
                  </button>
                )}

                {/* Debug Action Button */}
                <button 
                  className="action-btn btn-debug btn-sm"
                  onClick={(e) => debugContainer(container, e)}
                  title="Debug Container Information"
                >
                  <Bug size={14} />
                  <span>Debug</span>
                </button>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};

export default ContainerGrid;