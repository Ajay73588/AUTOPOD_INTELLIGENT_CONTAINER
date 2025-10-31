import React, { useState, useEffect } from 'react';
import { apiService } from '../services/api';
import '../styles/Logs.css';

const Logs = () => {
  const [logs, setLogs] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [containerFilter, setContainerFilter] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchLogs();
    const interval = setInterval(fetchLogs, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchLogs = async () => {
    try {
      const response = await apiService.getLogs();
      if (response.data.success) {
        setLogs(response.data.data || []);
      }
    } catch (error) {
      console.error('Error fetching logs:', error);
    } finally {
      setLoading(false);
    }
  };

  const filteredLogs = logs.filter(log => {
    const matchesSearch = searchQuery === '' || 
      log.log.toLowerCase().includes(searchQuery.toLowerCase()) ||
      log.container_name.toLowerCase().includes(searchQuery.toLowerCase());
    
    const matchesContainer = containerFilter === '' || 
      log.container_name === containerFilter;
    
    return matchesSearch && matchesContainer;
  });

  const uniqueContainers = [...new Set(logs.map(log => log.container_name))];

  const exportLogs = (format) => {
    const logText = filteredLogs.map(log => 
      `[${log.timestamp}] ${log.container_name}: ${log.log}`
    ).join('\n');
    
    const blob = new Blob([logText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `logs.${format}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const clearLogs = () => {
    setLogs([]);
  };

  return (
    <div className="logs-page">
      <div className="page-header">
        <h1>📝 Container Logs</h1>
        <p>Real-time container activity with filtering and search</p>
      </div>

      <div className="logs-controls">
        <div className="logs-filter-group">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search logs..."
            className="form-input"
          />
          <select 
            value={containerFilter}
            onChange={(e) => setContainerFilter(e.target.value)}
            className="form-input"
          >
            <option value="">All Containers</option>
            {uniqueContainers.map(container => (
              <option key={container} value={container}>{container}</option>
            ))}
          </select>
        </div>
        
        <div className="logs-actions">
          <button className="btn btn-secondary" onClick={fetchLogs}>
            <span className="btn-icon">🔄</span>
            <span className="btn-text">Refresh</span>
          </button>
          <button className="btn btn-secondary" onClick={() => exportLogs('txt')}>
            <span className="btn-icon">💾</span>
            <span className="btn-text">Export</span>
          </button>
          <button className="btn btn-secondary" onClick={clearLogs}>
            <span className="btn-icon">🧹</span>
            <span className="btn-text">Clear</span>
          </button>
        </div>
      </div>

      <div className="logs-container">
        {loading ? (
          <div className="loading">Loading logs...</div>
        ) : filteredLogs.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">📝</div>
            <h3>No Logs Found</h3>
            <p>{searchQuery || containerFilter ? 'No logs match your filters.' : 'No logs available. Start containers to see logs.'}</p>
          </div>
        ) : (
          <div className="logs-list">
            {filteredLogs.slice(-100).map((log, index) => ( // Show only last 100 logs
              <div key={index} className="log-entry">
                <span className="log-timestamp">[{log.timestamp}]</span>
                <span className="log-container">{log.container_name}:</span>
                <span className="log-message">{log.log}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="logs-info">
        Showing {filteredLogs.length} of {logs.length} total log entries
      </div>
    </div>
  );
};

export default Logs;