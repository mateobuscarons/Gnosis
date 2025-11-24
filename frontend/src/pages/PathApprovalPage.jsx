import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import './PathApprovalPage.css';

function PathApprovalPage({ sessionState, onComplete, viewOnly = false }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const learningPath = sessionState?.learning_path;
  const modules = learningPath?.learning_path?.modules || [];

  const handleApprove = async () => {
    setLoading(true);
    setError(null);

    try {
      await api.approvePath(learningPath);
      onComplete();
      navigate('/dashboard');
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };

  const handleReject = async () => {
    setLoading(true);
    setError(null);

    try {
      await api.reset();
      onComplete();
      navigate('/');
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };

  const handleReset = async () => {
    if (!window.confirm('Are you sure you want to reset the system? This will delete all your progress and learning path.')) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await api.reset();
      onComplete();
      navigate('/');
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };

  return (
    <div className="approval-page">
      <div className="approval-container">
        {viewOnly && (
          <button onClick={() => navigate('/dashboard')} className="back-button" style={{ marginBottom: '20px' }}>
            ← Back to Dashboard
          </button>
        )}
        <h1>{viewOnly ? 'Your Learning Path' : 'Review Your Learning Path'}</h1>
        <p className="subtitle">
          {viewOnly ? `${modules.length} modules for` : `Generated ${modules.length} modules for`}: {learningPath?.input?.learning_goal}
        </p>

        <div className="modules-list">
          {modules.map((module) => (
            <div key={module.module_number} className="module-card">
              <div className="module-header">
                <span className="module-number">Module {module.module_number}</span>
                <h3>{module.title}</h3>
              </div>
              <p className="module-description">{module.description}</p>

              <div className="module-details">
                <div>
                  <h4>Topics:</h4>
                  <ul>
                    {module.topics.map((topic, idx) => (
                      <li key={idx}>{topic}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <h4>Hands-on:</h4>
                  <ul>
                    {module.hands_on.map((exercise, idx) => (
                      <li key={idx}>{exercise}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          ))}
        </div>

        {error && <div className="error-message">{error}</div>}

        {!viewOnly ? (
          <>
            <div style={{ display: 'flex', gap: '15px', justifyContent: 'center' }}>
              <button
                className="approve-button"
                onClick={handleApprove}
                disabled={loading}
                style={{
                  background: '#28a745'
                }}
              >
                {loading ? 'Generating Challenges...' : 'Approve & Generate Challenges'}
              </button>

              <button
                className="approve-button"
                onClick={handleReject}
                disabled={loading}
                style={{
                  background: '#dc3545'
                }}
              >
                Reject & Start Over
              </button>
            </div>

            {loading && (
              <p className="loading-info">
                Generating challenges for {modules.length} modules... This may take 1-3 minutes.
              </p>
            )}
          </>
        ) : (
          <button
            className="reset-button"
            onClick={handleReset}
            disabled={loading}
            style={{
              backgroundColor: '#dc3545',
              marginTop: '20px'
            }}
          >
            {loading ? 'Resetting System...' : 'Reset System & Start Over'}
          </button>
        )}
      </div>
    </div>
  );
}

export default PathApprovalPage;
