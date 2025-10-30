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
    } finally {
      setLoading(false);
    }
  };

  const handleSync = async () => {
    try {
      await apiService.syncContainers();
      fetchDashboardData();
    } catch (error) {
      console.error('Error syncing containers:', error);
    }
  };

  if (loading) {
    return <div className="loading">Loading dashboard...</div>;
  }

  return (
    <div className="dashboard">
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
        <ContainerGrid containers={containers} showActions={true} />
      </section>
    </div>
  );
};

export default Dashboard;