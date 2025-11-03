import React, { useState, useEffect } from 'react';
import { apiService, checkBackendConnection, testContainerAction } from '../services/api';
import StatCard from '../components/StatCard';
import QuickActions from '../components/QuickActions';
import DeploymentSection from '../components/DeploymentSection';
import ContainerGrid from '../components/ContainerGrid';
import '../styles/Dashboard.css';

const Dashboard = () => {
  const [stats, setStats] = useState({
    total: 0,
    running: 0,
    stopped: 0,
    issues: 0
  });
  const [containers, setContainers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadingActions, setLoadingActions] = useState({});
  const [actionStatus, setActionStatus] = useState('');
  const [lastUpdated, setLastUpdated] = useState(null);
  const [healthStatus, setHealthStatus] = useState('checking');

  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchDashboardData = async () => {
    try {
      console.log('🔄 Fetching dashboard data...');
      const [statusRes, containersRes] = await Promise.all([
        apiService.getContainerStatus(),
        apiService.getContainers()
      ]);

      console.log('📊 Status response:', statusRes.data);
      console.log('📦 Containers response:', containersRes.data);

      if (statusRes.data.success) {
        const statusData = statusRes.data.data;
        const runningCount = statusData.filter(c => 
          c.status.toLowerCase().includes('running') || c.status.toLowerCase().includes('up')
        ).length;
        const stoppedCount = statusData.filter(c => 
          c.status.toLowerCase().includes('exited') || c.status.toLowerCase().includes('stopped')
        ).length;

        setStats({
          total: statusData.length,
          running: runningCount,
          stopped: stoppedCount,
          issues: statusData.length - runningCount - stoppedCount
        });
      }

      if (containersRes.data.success) {
        setContainers(containersRes.data.data.slice(0, 6));
      }

      setHealthStatus('healthy');
      setLastUpdated(new Date());
    } catch (error) {
      console.error('💥 Error fetching dashboard data:', error);
      setActionStatus('❌ Error fetching dashboard data');
      setHealthStatus('unhealthy');
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
    console.log(`🔄 Attempting to ${action} container:`, containerName);
    
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
          if (!window.confirm(`Are you sure you want to remove container ${containerName}?`)) {
            setActionStatus('');
            setActionLoading(containerName, action, false);
            return;
          }
          response = await apiService.removeContainer(containerName);
          break;
        default:
          setActionLoading(containerName, action, false);
          return;
      }

      console.log('📥 Action response:', response.data);
      
      if (response.data.success) {
        setActionStatus(`✅ Container ${containerName} ${action}ed successfully`);
        setTimeout(fetchDashboardData, 1000);
      } else {
        setActionStatus(`❌ Failed to ${action} container: ${response.data.error}`);
      }
    } catch (error) {
      console.error(`💥 Error ${action} container:`, error);
      let errorMessage = `❌ Error ${action}ing container: `;
      if (error.response?.data?.error) {
        errorMessage += error.response.data.error;
      } else if (error.message) {
        errorMessage += error.message;
      } else {
        errorMessage += 'Unknown error occurred';
      }
      setActionStatus(errorMessage);
    } finally {
      setActionLoading(containerName, action, false);
    }
  };

  const handleSync = async () => {
    try {
      setActionStatus('🔄 Syncing containers...');
      await apiService.syncContainers();
      setActionStatus('✅ Sync completed successfully');
      fetchDashboardData();
    } catch (error) {
      console.error('Error syncing containers:', error);
      setActionStatus('❌ Error syncing containers');
    }
  };

  const debugBackendConnection = async () => {
    try {
      setActionStatus('🔍 Testing backend connection...');
      const connection = await checkBackendConnection();
      
      if (connection.connected) {
        setActionStatus('✅ Backend is connected and responding!');
      } else {
        setActionStatus('❌ Backend connection failed: ' + connection.error);
      }
    } catch (error) {
      setActionStatus('❌ Debug test failed: ' + error.message);
    }
  };

  if (loading) {
    return (
      <div className="dashboard-loading">
        <div className="loading-spinner"></div>
        <p>Loading your container dashboard...</p>
      </div>
    );
  }

  return (
    <div className="dashboard">
      {/* Header Section */}
      <div className="dashboard-header">
        <div className="header-content">
          <div className="header-title">
            <h1>Container Dashboard</h1>
            <p>Manage and monitor your Docker containers</p>
          </div>
          <div className="header-status">
            <div className={`health-indicator ${healthStatus}`}>
              <div className="health-dot"></div>
              <span>System {healthStatus}</span>
            </div>
            {lastUpdated && (
              <div className="last-updated">
                Last updated: {lastUpdated.toLocaleTimeString()}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Status Message */}
      {actionStatus && (
        <div className={`status-message ${
          actionStatus.includes('✅') ? 'success' : 
          actionStatus.includes('🔍') || actionStatus.includes('🔄') ? 'info' :
          'error'
        }`}>
          <div className="status-content">
            <span className="status-icon">
              {actionStatus.includes('✅') ? '✓' : 
               actionStatus.includes('🔍') ? '🔍' :
               actionStatus.includes('🔄') ? '🔄' : '⚠'}
            </span>
            {actionStatus}
          </div>
          <button 
            className="status-close"
            onClick={() => setActionStatus('')}
          >
            ×
          </button>
        </div>
      )}

      {/* Quick Stats */}
      <div className="stats-section">
        <div className="section-header">
          <h2>📊 Overview</h2>
          <p>Real-time container statistics</p>
        </div>
        <div className="stats-grid">
          <StatCard
            icon="📦"
            label="Total Containers"
            value={stats.total}
            color="#3b82f6"
            trend="up"
          />
          <StatCard
            icon="✅"
            label="Running"
            value={stats.running}
            color="#10b981"
            trend="stable"
          />
          <StatCard
            icon="⏹️"
            label="Stopped"
            value={stats.stopped}
            color="#6b7280"
            trend="down"
          />
          <StatCard
            icon="⚠️"
            label="Issues"
            value={stats.issues}
            color="#ef4444"
            trend="warning"
          />
        </div>
      </div>

      {/* Quick Actions */}
      <QuickActions onSync={handleSync} onDebug={debugBackendConnection} />

      {/* Deployment Section */}
      <DeploymentSection />

      {/* Recent Containers */}
      <section className="section">
        <div className="section-header">
          <div className="section-title">
            <h2>📦 Recent Containers</h2>
            <span className="container-count">{containers.length} containers</span>
          </div>
          <p className="section-subtitle">Your recently active containers</p>
        </div>
        <ContainerGrid 
          containers={containers} 
          showActions={true} 
          onContainerAction={handleContainerAction}
          loadingActions={loadingActions}
        />
      </section>

      {/* Floating Action Button */}
      <button className="fab" onClick={handleSync} title="Sync Containers">
        <span className="fab-icon">🔄</span>
      </button>
    </div>
  );
};

export default Dashboard;