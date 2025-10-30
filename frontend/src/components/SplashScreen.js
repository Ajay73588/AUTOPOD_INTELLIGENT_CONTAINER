import React, { useEffect, useState } from 'react';
import '../styles/SplashScreen.css';

const SplashScreen = () => {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setVisible(false);
    }, 2500);

    return () => clearTimeout(timer);
  }, []);

  if (!visible) return null;

  return (
    <div className="splash-screen">
      <div className="splash-content">
        <div className="splash-icon">🚀</div>
        <h1 className="splash-title">AutoPod</h1>
        <p className="splash-subtitle">Intelligent Container Management</p>
        <div className="splash-loader">
          <div className="loader-dot"></div>
          <div className="loader-dot"></div>
          <div className="loader-dot"></div>
        </div>
      </div>
    </div>
  );
};

export default SplashScreen;