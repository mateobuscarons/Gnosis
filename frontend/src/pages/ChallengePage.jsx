import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Editor from '@monaco-editor/react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import MermaidDiagram from '../components/MermaidDiagram';
import { api } from '../services/api';
import './ChallengePage.css';

function ChallengePage({ onRefresh }) {
  const { moduleNumber, challengeNumber } = useParams();
  const navigate = useNavigate();

  const [challenge, setChallenge] = useState(null);
  const [userCode, setUserCode] = useState('');
  const [evaluation, setEvaluation] = useState(null);
  const [remediation, setRemediation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [viewMode, setViewMode] = useState('lesson'); // 'lesson' or 'challenge'

  // Custom components for ReactMarkdown with syntax highlighting and Mermaid
  const markdownComponents = {
    code({ node, inline, className, children, ...props }) {
      const match = /language-(\w+)/.exec(className || '');
      const language = match ? match[1] : '';

      // Force inline rendering for code without language class or explicit inline flag
      const isInline = inline || !className;

      // Render Mermaid diagrams
      if (!isInline && language === 'mermaid') {
        return <MermaidDiagram chart={String(children).replace(/\n$/, '')} />;
      }

      // Only use SyntaxHighlighter for actual code blocks (not inline code)
      return !isInline ? (
        <SyntaxHighlighter
          style={vscDarkPlus}
          language={language || 'python'}
          PreTag="div"
          {...props}
        >
          {String(children).replace(/\n$/, '')}
        </SyntaxHighlighter>
      ) : (
        <code className={className} {...props}>
          {children}
        </code>
      );
    },
    p({ node, children, ...props }) {
      // Ensure paragraphs don't add extra spacing around inline elements
      return <p style={{ margin: '0 0 16px 0' }} {...props}>{children}</p>;
    }
  };

  useEffect(() => {
    loadChallenge();
  }, [moduleNumber, challengeNumber]);

  const loadChallenge = async () => {
    setLoading(true);
    setEvaluation(null);
    setRemediation(null);
    setViewMode('lesson');

    try {
      const data = await api.getChallenge(moduleNumber, challengeNumber);
      setChallenge(data);

      // For conceptual challenges, start with empty string (no starter code)
      // For code challenges, use starter_code if provided
      const isConceptual = data.coding_challenge.challenge_format === 'conceptual';
      setUserCode(isConceptual ? '' : (data.coding_challenge.starter_code || ''));
    } catch (error) {
      console.error('Failed to load challenge:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async () => {
    setSubmitting(true);

    try {
      const result = await api.submitCode(moduleNumber, challengeNumber, userCode);
      setEvaluation(result.evaluation);
      setRemediation(result.remediation);

      if (result.evaluation.passed) {
        setTimeout(() => {
          onRefresh();
          navigate('/dashboard');
        }, 3000);
      }
    } catch (error) {
      console.error('Submission failed:', error);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="challenge-page">
        <div className="challenge-header">
          <button onClick={() => navigate('/dashboard')} className="back-button">
            ← Back to Dashboard
          </button>
        </div>
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <h2>Loading Challenge...</h2>
          <p>Preparing your lesson and coding challenge</p>
        </div>
      </div>
    );
  }

  return (
    <div className="challenge-page">
      <div className="challenge-header">
        <button onClick={() => navigate('/dashboard')} className="back-button">
          ← Back to Dashboard
        </button>
        <h1>
          Module {moduleNumber} - Challenge {challengeNumber}
        </h1>
        <p className="challenge-title">{challenge?.challenge_data?.title}</p>
      </div>

      <div className="challenge-content">
        {/* Lesson View - Full Screen */}
        {viewMode === 'lesson' && (
          <div className="lesson-fullscreen">
            <div className="lesson-content">
              <ReactMarkdown
                components={markdownComponents}
                remarkPlugins={[remarkGfm]}
              >
                {challenge?.lesson_markdown}
              </ReactMarkdown>
            </div>
            <button
              onClick={() => setViewMode('challenge')}
              className="start-challenge-button"
            >
              {userCode ? 'Continue Challenge' : 'Start Challenge'}
            </button>
          </div>
        )}

        {/* Challenge View - Full Screen */}
        {viewMode === 'challenge' && (
          <div className="challenge-fullscreen">
            <div className="challenge-prompt">
              <h3>Challenge</h3>
              <ReactMarkdown
                components={markdownComponents}
                remarkPlugins={[remarkGfm]}
              >
                {challenge?.coding_challenge?.challenge_prompt}
              </ReactMarkdown>
            </div>

            <div className="code-editor">
              {challenge?.coding_challenge?.challenge_format === 'conceptual' ? (
                <textarea
                  className="conceptual-input"
                  value={userCode}
                  onChange={(e) => setUserCode(e.target.value)}
                  placeholder="Write your answer here..."
                  rows={20}
                />
              ) : (
                <Editor
                  height="500px"
                  defaultLanguage="python"
                  value={userCode}
                  onChange={(value) => setUserCode(value || '')}
                  theme="vs-dark"
                  options={{
                    minimap: { enabled: false },
                    fontSize: 14,
                    lineNumbers: 'on',
                    scrollBeyondLastLine: false,
                    scrollbar: {
                      alwaysConsumeMouseWheel: false,
                    },
                  }}
                />
              )}
            </div>

            <div className="challenge-actions">
              <button
                onClick={() => setViewMode('lesson')}
                className="back-to-lesson-button"
              >
                ← Back to Lesson
              </button>

              <button
                onClick={handleSubmit}
                disabled={submitting || !userCode}
                className="submit-button"
              >
                {submitting ? 'Evaluating...' : 'Submit Solution'}
              </button>
            </div>

            {/* Only show hints from remediation, no evaluation details */}
            {remediation && (
              <div className="remediation">
                <h3>💡 Hint (Level {remediation.hint_level})</h3>
                <div className="remediation-content">
                  <ReactMarkdown
                    components={markdownComponents}
                    remarkPlugins={[remarkGfm]}
                  >
                    {remediation.targeted_hint}
                  </ReactMarkdown>
                </div>
                {remediation.encouragement && (
                  <p className="encouragement">{remediation.encouragement}</p>
                )}
                {remediation.key_concept_reminder && (
                  <div className="concept-reminder">
                    <strong>Remember:</strong> {remediation.key_concept_reminder}
                  </div>
                )}
              </div>
            )}

            {/* Success message only */}
            {evaluation && evaluation.passed && (
              <div className="success-message">
                <h3>✅ Challenge Passed!</h3>
                <p className="next-info">Redirecting to dashboard in 3 seconds...</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default ChallengePage;
