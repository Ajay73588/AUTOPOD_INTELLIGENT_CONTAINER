import React, { useState, useEffect } from 'react';
import { apiService } from '../services/api';

function Dashboard() {
  const [containers, setContainers] = useState([]);
  const [webhooks, setWebhooks] = useState([]);

  useEffect(() => {
    // Fetch containers
    apiService.getContainers()
      .then(response => setContainers(response.data.containers))
      .catch(error => console.error('Error fetching containers:', error));

    // Fetch webhooks
    apiService.getWebhooks()
      .then(response => setWebhooks(response.data.webhooks))
      .catch(error => console.error('Error fetching webhooks:', error));
  }, []);

  return (
    <div className="dashboard">
      <h1>AutoPod Intelligent Container</h1>
      
      <div className="containers-section">
        <h2>Containers</h2>
        <div className="containers-list">
          {containers.map(container => (
            <div key={container.id} className="container-item">
              {/* Render container details */}
            </div>
          ))}
        </div>
      </div>

      <div className="webhooks-section">
        <h2>Webhooks</h2>
        <div className="webhooks-list">
          {webhooks.map(webhook => (
            <div key={webhook.id} className="webhook-item">
              {/* Render webhook details */}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default Dashboard;