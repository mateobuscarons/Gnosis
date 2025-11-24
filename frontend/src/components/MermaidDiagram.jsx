import { useEffect, useRef } from 'react';
import mermaid from 'mermaid';

// Initialize mermaid with configuration
mermaid.initialize({
  startOnLoad: false,
  theme: 'default',
  securityLevel: 'loose',
  fontFamily: 'Arial, sans-serif',
});

function MermaidDiagram({ chart }) {
  const elementRef = useRef(null);

  useEffect(() => {
    if (elementRef.current && chart) {
      try {
        // Generate unique ID for this diagram
        const id = `mermaid-${Math.random().toString(36).substr(2, 9)}`;

        // Render the diagram
        mermaid.render(id, chart).then(({ svg }) => {
          if (elementRef.current) {
            elementRef.current.innerHTML = svg;
          }
        });
      } catch (error) {
        console.error('Mermaid rendering error:', error);
        if (elementRef.current) {
          elementRef.current.innerHTML = `<pre>Error rendering diagram:\n${chart}</pre>`;
        }
      }
    }
  }, [chart]);

  return <div ref={elementRef} className="mermaid" />;
}

export default MermaidDiagram;
