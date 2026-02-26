import { useState, useEffect } from 'react'
import { Mic, Settings, MessageSquare, Maximize2, X } from 'lucide-react'
import './App.css'

// TypeScript declarations for the Qt bridge
declare global {
  interface Window {
    qt: any;
    bridge: any;
  }
}

function App() {
  const [isLive, setIsLive] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [transcript, setTranscript] = useState("Waiting for interview audio...")
  const [aiResponse, setAiResponse] = useState("Nebula AI is ready to assist you. Start your session to begin.")
  const [status, setStatus] = useState("Initializing...")

  useEffect(() => {
    let bridgeInitAttempt = 0;
    const maxAttempts = 50;

    const initBridge = () => {
      if (window.qt && window.qt.webChannelTransport && (window as any).QWebChannel) {
        new (window as any).QWebChannel(window.qt.webChannelTransport, (channel: any) => {
          window.bridge = channel.objects.bridge;
          setStatus("V7.0 Ready");

          window.bridge.transcriptReceived.connect((text: string) => {
            setTranscript(text);
            setDrawerOpen(true);
          });

          window.bridge.aiResponseReceived.connect((response: string) => {
            setAiResponse(response);
          });

          window.bridge.syncStatusUpdated.connect((msg: string) => {
            setStatus(msg);
          });
        });
      } else if (bridgeInitAttempt < maxAttempts) {
        bridgeInitAttempt++;
        setTimeout(initBridge, 200);
      } else {
        setStatus("System Offline");
      }
    };

    initBridge();
  }, []);

  const toggleListening = () => {
    const newState = !isLive;
    setIsLive(newState);
    if (window.bridge) {
      window.bridge.toggleListening(newState);
    }
  };

  return (
    <div className="app-container">
      {/* Floating Pill Interface */}
      <div className="floating-pill">
        <div className="pill-content">
          <div className="status-group">
            <div className={`status-dot ${isLive ? 'live' : ''}`} />
            <div className="title-group">
              <span className="title">Nebula Assistant</span>
              <span className="subtitle">{status}</span>
            </div>
          </div>

          <div className="action-bar">
            <button className="icon-btn" title="Context Info">
              <MessageSquare size={18} />
            </button>
            <button className="icon-btn" title="Settings">
              <Settings size={18} />
            </button>
            <button
              className={`icon-btn ${isLive ? 'primary' : ''}`}
              onClick={toggleListening}
              title={isLive ? "Stop Listening" : "Start Listening"}
            >
              <Mic size={18} />
            </button>
            <button
              className="icon-btn"
              onClick={() => setDrawerOpen(!drawerOpen)}
              title="Expand Details"
            >
              <Maximize2 size={18} />
            </button>
            <button className="icon-btn" onClick={() => window.close()} title="Close">
              <X size={18} />
            </button>
          </div>
        </div>
      </div>

      {/* Response Drawer */}
      {drawerOpen && (
        <div className="response-drawer">
          <div className="transcript-area">
            <span style={{ color: 'var(--text-dim)', marginRight: '8px', fontSize: '11px', fontWeight: 700 }}>LIVE TRANSCRIPT</span>
            <p>{transcript}</p>
          </div>
          <div className="ai-response">
            <span style={{ color: 'var(--accent-primary)', display: 'block', marginBottom: '8px', fontSize: '11px', fontWeight: 700 }}>NEBULA AI GUIDANCE</span>
            <p>{aiResponse}</p>
          </div>
        </div>
      )}
    </div>
  )
}

export default App
