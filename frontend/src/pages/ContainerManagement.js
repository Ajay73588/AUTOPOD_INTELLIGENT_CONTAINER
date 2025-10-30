import React, { useState, useEffect } from 'react';
import { apiService } from '../services/api';
import ContainerGrid from '../components/ContainerGrid';
import ContainerActions from '../components/ContainerActions';
import '../styles/ContainerManagement.css';

const ContainerManagement = () => {
  const [containers, setContainers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedContainer, setSelectedContainer] = useState(null);

  useEffect(() => {
    fetchContainers();
    const interval = setInterval(fetchContainers, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchContainers = async () => {
    try {
      const response = await apiService.getContainers();
      if (response.data.success) {
        setContainers(response.data.data);
      }
    } catch (error) {
      console.error('Error fetching containers:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleContainerAction = async (action, containerName) => {
    try {
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
          if (!window.confirm(`Are you sure you want to remove container ${containerName}?`)) {
            return;
          }
          response = await apiService.removeContainer(containerName);
          break;
        default:
          return;
      }

      if (response.data.success) {
        fetchContainers();
      }
    } catch (error) {
      console.error(`Error ${action} container:`, error);
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

      <div className="management-layout">
        <div className="containers-section">
          <ContainerGrid
            containers={containers}
            showActions={true}
            onContainerAction={handleContainerAction}
            onContainerSelect={setSelectedContainer}
            selectedContainer={selectedContainer}
          />
        </div>

        {selectedContainer && (
          <div className="details-section">
            <ContainerActions
              container={selectedContainer}
              onAction={handleContainerAction}
            />
          </div>
        )}
      </div>
    </div>
  );
};

export default ContainerManagement;