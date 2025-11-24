import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { api } from './services/api';
import SetupPage from './pages/SetupPage';
import PathApprovalPage from './pages/PathApprovalPage';
import Dashboard from './pages/Dashboard';
import ChallengePage from './pages/ChallengePage';
import './App.css';

function App() {
  const [sessionState, setSessionState] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadSession();
  }, []);

  const loadSession = async () => {
    try {
      const session = await api.getSession();
      console.log('📊 Session loaded:', session);
      console.log('   State:', session.state);
      console.log('   User:', session.user_profile);
      console.log('   Learning Path:', session.learning_path ? 'EXISTS' : 'NULL');
      setSessionState(session);
    } catch (error) {
      console.error('Failed to load session:', error);
    } finally {
      setLoading(false);
    }
  };

  const refreshSession = () => {
    setLoading(true);
    loadSession();
  };

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="spinner"></div>
        <p>Loading...</p>
      </div>
    );
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/"
          element={
            sessionState?.state === 'new_user' ? (
              <SetupPage onComplete={refreshSession} />
            ) : sessionState?.state === 'path_approval' ? (
              <Navigate to="/approve" replace />
            ) : (
              <Navigate to="/dashboard" replace />
            )
          }
        />
        <Route
          path="/approve"
          element={<PathApprovalPage sessionState={sessionState} onComplete={refreshSession} />}
        />
        <Route
          path="/path/view"
          element={<PathApprovalPage sessionState={sessionState} onComplete={refreshSession} viewOnly={true} />}
        />
        <Route
          path="/dashboard"
          element={<Dashboard sessionState={sessionState} onRefresh={refreshSession} />}
        />
        <Route
          path="/challenge/:moduleNumber/:challengeNumber"
          element={<ChallengePage onRefresh={refreshSession} />}
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
