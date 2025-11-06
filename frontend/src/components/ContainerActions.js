import React from 'react';
import { Play, Square, RotateCcw, Trash2, Globe, Loader } from 'lucide-react';

const ContainerActions = ({ container, onAction, loadingActions = {} }) => {
  const containerName = container.Names?.[0] || container.container_name;
  const status = container.Status || container.status || 'Unknown';
  const image = container.Image || container.image || 'N/A';
  const created = container.Created || container.created_at;
  const ports = container.Ports || [];
  
  const isRunning = status.toLowerCase().includes('running');
  const isStopped = status.toLowerCase().includes('exited') || status.toLowerCase().includes('stopped');

  const isActionLoading = (action) => {
    return loadingActions[`${containerName}_${action}`] || false;
  };

  const actions = [
    {
      icon: Play,
      label: 'Start Container',
      color: 'success',
      action: 'start',
      disabled: isRunning || isActionLoading('start'),
      description: 'Start the container if it\'s stopped',
      loading: isActionLoading('start')
    },
    {
      icon: Square,
      label: 'Stop Container',
      color: 'warning',
      action: 'stop',
      disabled: !isRunning || isActionLoading('stop'),
      description: 'Gracefully stop the container',
      loading: isActionLoading('stop')
    },
    {
      icon: RotateCcw,
      label: 'Restart Container',
      color: 'secondary',
      action: 'restart',
      disabled: !isRunning || isActionLoading('restart'),
      description: 'Restart the running container',
      loading: isActionLoading('restart')
    },
    {
      icon: Trash2,
      label: 'Remove Container',
      color: 'danger',
      action: 'remove',
      disabled: isActionLoading('remove'),
      description: 'Remove the container (cannot be undone)',
      loading: isActionLoading('remove')
    }
  ];

  const formatDate = (dateValue) => {
    try {
      if (typeof dateValue === 'number') {
        return new Date(dateValue * 1000).toLocaleString();
      }
      return new Date(dateValue).toLocaleString();
    } catch {
      return 'Unknown';
    }
  };

  const openWebInterface = () => {
    if (ports.length > 0) {
      const port = ports[0];
      const url = `http://localhost:${port.PublicPort || port.HostPort}`;
      window.open(url, '_blank');
    }
  };

  return (
    <div className="container-actions-panel">
      <div className="panel-header">
        <h3>Container Actions</h3>
        <div className="status-indicator">
          <div className={`status-dot ${isRunning ? 'running' : 'stopped'}`}></div>
          <span>{isRunning ? 'Running' : 'Stopped'}</span>
        </div>
      </div>

      <div className="action-buttons">
        {actions.map((action, index) => {
          const Icon = action.icon;
          return (
            <div key={index} className="action-item">
              <button
                className={`btn btn-${action.color} action-btn`}
                onClick={() => onAction(action.action, containerName)}
                disabled={action.disabled}
                title={action.description}
              >
                {action.loading ? (
                  <Loader size={18} className="spin" />
                ) : (
                  <Icon size={18} />
                )}
                <span>
                  {action.loading ? `${action.label}...` : action.label}
                </span>
              </button>
              <div className="action-description">
                {action.description}
              </div>
            </div>
          );
        })}

        {ports.length > 0 && isRunning && (
          <div className="action-item">
            <button
              className="btn btn-primary action-btn"
              onClick={openWebInterface}
              title="Open web interface in browser"
            >
              <Globe size={18} />
              <span>Open Web UI</span>
            </button>
            <div className="action-description">
              Open container's web interface
            </div>
          </div>
        )}
      </div>
      
      {/* ... rest of the component remains the same ... */}
    </div>
  );
};

export default ContainerActions;