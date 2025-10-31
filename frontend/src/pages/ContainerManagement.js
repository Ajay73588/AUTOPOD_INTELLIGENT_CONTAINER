import React, { useState, useEffect } from 'react';
import { apiService } from '../services/api';
import ContainerGrid from '../components/ContainerGrid';
import ContainerActions from '../components/ContainerActions';
import '../styles/ContainerManagement.css';

const ContainerManagement = () => {
  const [containers, setContainers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedContainer, setSelectedContainer] = useState(null);
  const [actionStatus, setActionStatus] = useState('');
  const [loadingActions, setLoadingActions] = useState({}); // Track loading states

  useEffect(() => {
    fetchContainers();
    const interval = setInterval(fetchContainers, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchContainers = async () => {
    try {
      const response = await apiService.getContainers();
      if (response.data.success) {
        setContainers(response.data.data || []);
        
        // Keep the selected container updated if it exists
        if (selectedContainer) {
          const updatedContainer = (response.data.data || []).find(
            container => container.Names?.[0] === selectedContainer.Names?.[0]
          );
          if (updatedContainer) {
            setSelectedContainer(updatedContainer);
          }
        }
      }
    } catch (error) {
      console.error('Error fetching containers:', error);
      setActionStatus('Error fetching containers');
    } finally {
      setLoading(false);
    }
  };

  const setActionLoading = (containerName, action, isLoading) => {
    setLoadingActions(prev => ({
      ...prev,
      [`${containerName}_${action}`]: isLoading
    }));
  };

  const handleContainerAction = async (action, containerName) => {
    try {
      setActionLoading(containerName, action, true);
      setActionStatus(`${action}ing container ${containerName}...`);
      
      let response;
      switch (action) {
        case 'start':
          response = await apiService.startContainer(containerName);
          break;
        case 'stop':
          response = await apiService.stopContainer(containerName);
          break;
        case 'restart':
          response = await apiService.restartContainer(containerName);
          break;
        case 'remove':
          if (!window.confirm(`Are you sure you want to remove container ${containerName}? This action cannot be undone.`)) {
            setActionStatus('');
            setActionLoading(containerName, action, false);
            return;
          }
          response = await apiService.removeContainer(containerName);
          // Clear selection if the removed container was selected
          if (selectedContainer && (selectedContainer.Names?.[0] === containerName || selectedContainer.container_name === containerName)) {
            setSelectedContainer(null);
          }
          break;
        default:
          setActionLoading(containerName, action, false);
          return;
      }

      if (response.data.success) {
        setActionStatus(`✅ Container ${containerName} ${action}ed successfully`);
        // Refresh containers after action
        setTimeout(fetchContainers, 1000);
      } else {
        setActionStatus(`❌ Failed to ${action} container: ${response.data.error}`);
      }
    } catch (error) {
      console.error(`Error ${action} container:`, error);
      setActionStatus(`❌ Error ${action}ing container: ${error.message}`);
    } finally {
      setActionLoading(containerName, action, false);
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
      </div>

      {actionStatus && (
        <div className={`status-message ${actionStatus.includes('✅') ? 'success' : 'error'}`}>
          {actionStatus}
        </div>
      )}

      <div className="management-layout">
        <div className="containers-section">
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