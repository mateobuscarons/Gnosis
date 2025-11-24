import { useState } from 'react';
import { api } from '../services/api';
import './SetupPage.css';

function SetupPage({ onComplete }) {
  const [learningGoal, setLearningGoal] = useState('');
  const [experienceLevel, setExperienceLevel] = useState('Beginner');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      await api.setup(learningGoal, experienceLevel);
      onComplete();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="setup-page">
      <div className="setup-container">
        <h1>Adaptive Learning OS</h1>
        <p className="subtitle">AI-powered personalized technical learning</p>

        <form onSubmit={handleSubmit} className="setup-form">
          <div className="form-group">
            <label htmlFor="learning-goal">What do you want to learn?</label>
            <input
              id="learning-goal"
              type="text"
              value={learningGoal}
              onChange={(e) => setLearningGoal(e.target.value)}
              placeholder="e.g., Build REST APIs with FastAPI"
              required
              disabled={loading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="experience-level">Your experience with the topic:</label>
            <select
              id="experience-level"
              value={experienceLevel}
              onChange={(e) => setExperienceLevel(e.target.value)}
              disabled={loading}
            >
              <option value="Beginner">Beginner</option>
              <option value="Intermediate">Intermediate</option>
              <option value="Advanced">Advanced</option>
            </select>
          </div>

          {error && <div className="error-message">{error}</div>}

          <button type="submit" disabled={loading || !learningGoal}>
            {loading ? 'Generating Learning Path...' : 'Generate Learning Path'}
          </button>

          {loading && (
            <p className="loading-info">
              This may take 30-60 seconds. Please wait...
            </p>
          )}
        </form>
      </div>
    </div>
  );
}

export default SetupPage;
