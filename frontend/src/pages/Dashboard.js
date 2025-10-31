import React, { useState, useEffect } from 'react';
import { apiService } from '../services/api';
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

  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchDashboardData = async () => {
    try {
      const [statusRes, containersRes] = await Promise.all([
        apiService.getContainerStatus(),
        apiService.getContainers()
      ]);

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
        setContainers(containersRes.data.data.slice(0, 6)); // Show only 6 on dashboard
      }
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
      setActionStatus('Error fetching dashboard data');
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

      if (response.data.success) {
        setActionStatus(`✅ Container ${containerName} ${action}ed successfully`);
        setTimeout(fetchDashboardData, 1000);
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

  const handleSync = async () => {
    try {
      setActionStatus('Syncing containers...');
      await apiService.syncContainers();
      setActionStatus('✅ Sync completed successfully');
      fetchDashboardData();
    } catch (error) {
      console.error('Error syncing containers:', error);
      setActionStatus('❌ Error syncing containers');
    }
  };

  if (loading) {
    return <div className="loading">Loading dashboard...</div>;
  }

  return (
    <div className="dashboard">
      {actionStatus && (
        <div className={`status-message ${actionStatus.includes('✅') ? 'success' : 'error'}`}>
          {actionStatus}
        </div>
      )}

      {/* Quick Stats */}
      <div className="stats-grid">
        <StatCard
          icon="📦"
          label="Total Containers"
          value={stats.total}
          color="#3b82f6"
        />
        <StatCard
          icon="✅"
          label="Running"
          value={stats.running}
          color="#10b981"
        />
        <StatCard
          icon="⏹️"
          label="Stopped"
          value={stats.stopped}
          color="#6b7280"
        />
        <StatCard
          icon="⚠️"
          label="Issues"
          value={stats.issues}
          color="#ef4444"
        />
      </div>

      {/* Quick Actions */}
      <QuickActions onSync={handleSync} />

      {/* Deployment Section */}
      <DeploymentSection />

      {/* Recent Containers */}
      <section className="section">
        <div className="section-header">
          <h2>📦 Recent Containers</h2>
          <p className="section-subtitle">Your recently active containers</p>
        </div>
        <ContainerGrid 
          containers={containers} 
          showActions={true} 
          onContainerAction={handleContainerAction}
          loadingActions={loadingActions}
        />
      </section>
    </div>
  );
};

export default Dashboard;