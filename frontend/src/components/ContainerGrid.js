import React from 'react';
import { Play, Square, RotateCcw, Trash2, ExternalLink, Loader } from 'lucide-react';
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

  const handleAction = (action, containerName, e) => {
    e.stopPropagation();
    if (onContainerAction) {
      onContainerAction(action, containerName);
    }
  };

  const handleContainerClick = (container) => {
    if (onContainerSelect) {
      onContainerSelect(container);
    }
  };

  const isActionLoading = (containerName, action) => {
    return loadingActions[`${containerName}_${action}`] || false;
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
        const containerName = container.Names?.[0] || container.container_name || `container-${index}`;
        const status = container.Status || container.status || 'Unknown';
        const image = container.Image || container.image || 'N/A';
        const created = container.Created || container.created_at;
        const ports = container.Ports || [];
        
        const isRunning = status.toLowerCase().includes('running');
        const isStopped = status.toLowerCase().includes('exited') || status.toLowerCase().includes('stopped');

        const isSelected = selectedContainer && 
          (selectedContainer.Names?.[0] === containerName || 
           selectedContainer.container_name === containerName);

        return (
          <div 
            key={container.Id || container.id || index}
            className={`container-card ${isSelected ? 'selected' : ''}`}
            onClick={() => handleContainerClick(container)}
          >
            <div className="container-header">
              <div className="container-name-section">
                <div className="container-icon">🐳</div>
                <div className="container-name">{containerName}</div>
              </div>
              <span className={`status-badge ${getStatusBadge(status)}`}>
                {getStatusText(status)}
              </span>
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
                <span className="detail-label">Created:</span>
                <span className="detail-value">{formatDate(created)}</span>
              </div>

              {ports.length > 0 && (
                <div className="detail-item">
                  <span className="detail-label">Ports:</span>
                  <span className="detail-value ports">
                    {ports.map(port => 
                      `${port.PublicPort || port.HostPort || 'N/A'}:${port.PrivatePort || port.ContainerPort || 'N/A'}`
                    ).join(', ')}
                  </span>
                </div>
              )}
            </div>

            {showActions && (
              <div className="container-actions">
                <button 
                  className="action-btn btn-success btn-sm"
                  onClick={(e) => handleAction('start', containerName, e)}
                  disabled={isRunning || isActionLoading(containerName, 'start')}
                  title="Start Container"
                >
                  {isActionLoading(containerName, 'start') ? (
                    <Loader size={14} className="spin" />
                  ) : (
                    <Play size={14} />
                  )}
                  <span>
                    {isActionLoading(containerName, 'start') ? 'Starting...' : 'Start'}
                  </span>
                </button>
                
                <button 
                  className="action-btn btn-warning btn-sm"
                  onClick={(e) => handleAction('stop', containerName, e)}
                  disabled={!isRunning || isActionLoading(containerName, 'stop')}
                  title="Stop Container"
                >
                  {isActionLoading(containerName, 'stop') ? (
                    <Loader size={14} className="spin" />
                  ) : (
                    <Square size={14} />
                  )}
                  <span>
                    {isActionLoading(containerName, 'stop') ? 'Stopping...' : 'Stop'}
                  </span>
                </button>
                
                <button 
                  className="action-btn btn-secondary btn-sm"
                  onClick={(e) => handleAction('restart', containerName, e)}
                  disabled={!isRunning || isActionLoading(containerName, 'restart')}
                  title="Restart Container"
                >
                  {isActionLoading(containerName, 'restart') ? (
                    <Loader size={14} className="spin" />
                  ) : (
                    <RotateCcw size={14} />
                  )}
                  <span>
                    {isActionLoading(containerName, 'restart') ? 'Restarting...' : 'Restart'}
                  </span>
                </button>
                
                <button 
                  className="action-btn btn-danger btn-sm"
                  onClick={(e) => handleAction('remove', containerName, e)}
                  disabled={isActionLoading(containerName, 'remove')}
                  title="Remove Container"
                >
                  {isActionLoading(containerName, 'remove') ? (
                    <Loader size={14} className="spin" />
                  ) : (
                    <Trash2 size={14} />
                  )}
                  <span>
                    {isActionLoading(containerName, 'remove') ? 'Removing...' : 'Remove'}
                  </span>
                </button>

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
                        window.open(url, '_blank');
                      }
                    }}
                    title="Open Web Interface"
                  >
                    <ExternalLink size={14} />
                    <span>Open</span>
                  </button>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};

export default ContainerGrid;