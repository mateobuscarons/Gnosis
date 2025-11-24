import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import './Dashboard.css';

function Dashboard({ sessionState, onRefresh }) {
  const [progress, setProgress] = useState(null);
  const [challengesMetadata, setChallengesMetadata] = useState({});
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    loadProgress();
  }, []);

  const loadProgress = async () => {
    try {
      const [progressData, metadataData] = await Promise.all([
        api.getProgress(),
        api.getChallengesMetadata()
      ]);
      setProgress(progressData);
      setChallengesMetadata(metadataData);
    } catch (error) {
      console.error('Failed to load progress:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleChallengeClick = (moduleNum, challengeNum) => {
    navigate(`/challenge/${moduleNum}/${challengeNum}`);
  };

  if (loading) {
    return <div className="loading">Loading progress...</div>;
  }

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h1>Your Learning Journey</h1>
          <button
            onClick={() => navigate('/path/view')}
            style={{
              padding: '10px 20px',
              backgroundColor: '#007bff',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '14px'
            }}
          >
            View Learning Path
          </button>
        </div>
        <div className="progress-bar">
          <div
            className="progress-fill"
            style={{ width: `${progress?.completion_percentage || 0}%` }}
          />
          <span className="progress-text">
            {progress?.total_completed || 0} / {progress?.total_challenges || 0} completed
            ({Math.round(progress?.completion_percentage || 0)}%)
          </span>
        </div>
      </header>

      <div className="modules-grid">
        {progress?.modules?.map((module) => (
          <div key={module.module_number} className="module-section">
            <div className="module-title">
              <h2>Module {module.module_number}</h2>
              <span className="module-progress">
                {module.completed}/{module.total}
              </span>
            </div>

            <div className="challenges-list">
              {Array.from({ length: module.total }, (_, i) => {
                const challengeNum = i + 1;
                // Get actual completion status from individual challenge details
                const challengeDetail = module.challenge_details?.[challengeNum];
                const isCompleted = challengeDetail?.completed || false;

                const moduleMetadata = challengesMetadata[module.module_number] || [];
                const challengeInfo = moduleMetadata.find(c => c.challenge_number === challengeNum);

                return (
                  <div
                    key={challengeNum}
                    className={`challenge-item ${isCompleted ? 'completed' : 'not-started'}`}
                    onClick={() => handleChallengeClick(module.module_number, challengeNum)}
                  >
                    <div className="challenge-main">
                      <span className="challenge-number">{challengeNum}</span>
                      <span className="challenge-status">
                        {isCompleted ? '✓' : '○'}
                      </span>
                      {challengeInfo && (
                        <div className="challenge-title">{challengeInfo.title}</div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default Dashboard;
