import { useState, useEffect, useRef } from 'react'
import {
  Settings,
  Sparkles,
  User,
  Shield,
  Zap,
  Globe,
  Terminal,
  Copy,
  Check,
  Lock,
  X,
  Mic,
  Play,
  Pause,
  Upload,
  KeyRound,
  LogIn,
  Mail,
  Github,
  Type
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import './App.css'

declare global {
  interface Window {
    electron: any;
  }
}

type DrawerMode = 'response' | 'account' | 'settings' | 'strategy';

// --- Animation Constants (Premium Suite v27.0) ---
const SESSION_DURATION_MS = 15 * 60 * 1000; // 15 minutes (server-driven)

const springGentle: any = { type: "spring", stiffness: 300, damping: 30 };
const springQuick: any = { type: "spring", stiffness: 450, damping: 25 };

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.08, delayChildren: 0.1 }
  }
};

const pillVariants = {
  hidden: { opacity: 0, scale: 0.9, y: 10 },
  visible: {
    opacity: 1, scale: 1, y: 0,
    transition: springGentle
  },
  exit: { opacity: 0, scale: 0.9, y: 5, transition: { duration: 0.2 } }
};

function formatCountdown(ms: number): string {
  if (ms <= 0) return "00:00";
  const totalSec = Math.floor(ms / 1000);
  const m = Math.floor(totalSec / 60).toString().padStart(2, '0');
  const s = (totalSec % 60).toString().padStart(2, '0');
  return `${m}:${s} `;
}

function App() {
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [drawerMode, setDrawerMode] = useState<DrawerMode>('response')
  const [isLive, setIsLive] = useState(false)
  const [status, setStatus] = useState("V20.3 PRO")
  const [isError, setIsError] = useState(false)
  const [showOnboarding, setShowOnboarding] = useState(false)
  const [platform, setPlatform] = useState<string>('win32')

  const [transcript, setTranscript] = useState("")
  const [aiResponse, setAiResponse] = useState("")
  const [history, setHistory] = useState<{ q: string, a: string, strategy: string }[]>([])
  const [account, setAccount] = useState<any>({ display_name: "", email: "", credits: 0, plan: "GUEST" })
  const [contextText, setContextText] = useState("")
  const [detectedStrategy, setDetectedStrategy] = useState<string | null>(null)

  const [isLoggingIn, setIsLoggingIn] = useState(false)
  const [loginEmail, setLoginEmail] = useState("")
  const [loginToken, setLoginToken] = useState("")
  const [sessionId] = useState(() => Math.random().toString(36).substring(7))

  // --- Session Timer ---
  const [sessionStartTime, setSessionStartTime] = useState<number | null>(null)
  const [remainingMs, setRemainingMs] = useState<number>(SESSION_DURATION_MS)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const [settings, setSettings] = useState<any>({
    stealth_mode: false,
    save_transcripts: false,
    text_size: 15,
    low_credit_alert: true,
    session_end_warning: true,
    autoload_resume: false,
    show_guide_startup: true,
    light_mode: false,
    opacity: 255,
    hotkey: 'F2',
    expert_mode: 'Standard assistant'
  })

  const sessionActive = sessionStartTime !== null && remainingMs > 0;
  // Authorized = (signed in + at least 1 credit) OR an active session window
  const isAuthorized = (account.email && account.plan !== "GUEST") || sessionActive;
  const timerUrgent = remainingMs <= 5 * 60 * 1000; // < 5 min

  // Start or resume the countdown interval from remaining seconds
  const startCountdown = (remainingSeconds: number) => {
    if (timerRef.current) clearInterval(timerRef.current);
    const startedAt = Date.now();
    const initialMs = remainingSeconds * 1000;
    setRemainingMs(initialMs);
    setSessionStartTime(startedAt);

    timerRef.current = setInterval(() => {
      const elapsed = Date.now() - startedAt;
      const remaining = initialMs - elapsed;
      if (remaining <= 0) {
        setRemainingMs(0);
        if (timerRef.current) clearInterval(timerRef.current);
        timerRef.current = null;
        // Stop listening — credit was already deducted when session started
        setIsLive(false);
        window.electron.ipcRenderer.send('toggle-listening', false);
        window.electron.ipcRenderer.send('send-to-sidecar', { action: 'session-expired' });
        setSessionStartTime(null);
      } else {
        setRemainingMs(remaining);
      }
    }, 1000);
  };

  useEffect(() => {
    if (!window.electron) return;

    window.electron.ipcRenderer.invoke('get-platform').then((p: string) => setPlatform(p));

    window.electron.ipcRenderer.on('status-received', (s: any) => {
      console.log("UI: Status Message:", s.msg);
      if (s.msg) {
        setStatus(s.msg);
        // Reset error state if we get a standard status
        if (!s.is_error) setIsError(false);
      }
    });

    window.electron.ipcRenderer.on('error-received', (e: any) => {
      console.error("UI: Error Received:", e.msg);
      setStatus(e.msg || "AI Error");
      setIsError(true);
    });

    window.electron.ipcRenderer.on('transcript-received', (t: any) => {
      console.log("UI: Transcription Received:", t.text);
      setTranscript(t.text);
      // Removed clearing aiResponse here to prevent flickering/loss of response
    });

    window.electron.ipcRenderer.on('ai-response-received', (p: any) => {
      console.log("UI: AI Response Received (Length:", p.text?.length, ")");
      setAiResponse(p.text);
      setTranscript(""); // Clear transcript to prevent duplicate pills v23.2

      // Update History Stack (v20.0 Persistent Buttons)
      if (p.text && p.trigger_question) {
        setHistory(prev => {
          // Prevent exact duplicate questions stacking
          if (prev.length > 0 && prev[prev.length - 1].q === p.trigger_question) return prev;
          const newHistory = [...prev, { q: p.trigger_question, a: p.text, strategy: p.strategy || "Standard" }];
          return newHistory.slice(-4); // Keep maximum 4 pills v26.1
        });
      }

      if (p.strategy) {
        setDetectedStrategy(p.strategy);
        if (p.provider) setStatus(`AI: ${p.provider} OK`);
      }
      setDrawerMode('response');
      setDrawerOpen(true);
    });

    window.electron.ipcRenderer.on('ai-chunk-received', (p: any) => {
      console.log("UI: AI Chunk Received:", p.text, "Strategy:", p.strategy);
      if (p.text === "") {
        setAiResponse(""); // Clear exclusively when a NEW generation starts
        setTranscript(""); // Clear transcript for new generation start v23.2
      } else {
        setAiResponse(prev => prev + p.text);
      }
      if (p.strategy) setDetectedStrategy(p.strategy);
      setDrawerOpen(true);
      setDrawerMode('response');
    });

    window.electron.ipcRenderer.on('error-received', (e: any) => {
      console.error("UI: Process Error Received:", e.msg);
      if (e.msg.includes("429") || e.msg.includes("Quota")) {
        setStatus("QUOTA EXCEEDED (Wait 60s)");
      } else {
        setStatus(`ERROR: ${e.msg}`);
      }
    });

    // Global Debug Helper for User
    (window as any).nebulaTestAI = () => {
      console.log("UI: Executing Global console test...");
      window.electron.ipcRenderer.send('send-to-sidecar', {
        action: 'fake-transcript',
        payload: 'Global Console Test: Respond with "HELLO FROM BRAIN".'
      });
    };
    window.electron.ipcRenderer.on('account-info-received', (p: any) => {
      console.log("UI: Account Info Received ->", p);
      setAccount((prev: any) => ({ ...prev, ...p }));
      setIsLoggingIn(false);
    });
    window.electron.ipcRenderer.on('context-fetched-received', (p: any) => setContextText(p.text));
    window.electron.ipcRenderer.on('settings-data-received', (p: any) => {
      setSettings(p);
      window.electron.ipcRenderer.send('update-stealth', p.stealth_mode);
      window.electron.ipcRenderer.send('set-opacity', p.opacity);
      window.electron.ipcRenderer.send('re-register-hotkey', p.hotkey);
    });
    window.electron.ipcRenderer.on('hotkey-triggered', () => {
      if (!isAuthorized) return;
      setIsLive(prev => {
        const ns = !prev;
        window.electron.ipcRenderer.send('toggle-listening', ns);
        return ns;
      });
    });
    window.electron.ipcRenderer.on('auth-complete', (p: any) => {
      if (p.success) {
        setIsLoggingIn(false);
        window.electron.ipcRenderer.send('send-to-sidecar', { action: 'fetch-account' });
      }
    });

    // Restore session from sidecar on startup (server-driven)
    window.electron.ipcRenderer.on('session-status-received', (p: any) => {
      if (p.active && p.remaining_seconds > 0) {
        startCountdown(p.remaining_seconds);
      }
    });

    // Handle session start response
    window.electron.ipcRenderer.on('session-started-received', (p: any) => {
      if (p.success) {
        startCountdown(p.remaining_seconds);
      } else {
        // Failed to start session (no credits, server error, etc.)
        setIsLive(false);
        window.electron.ipcRenderer.send('toggle-listening', false);
      }
    });

    window.electron.ipcRenderer.send('send-to-sidecar', { action: 'get-settings' });
    window.electron.ipcRenderer.send('send-to-sidecar', { action: 'fetch-account' });
    window.electron.ipcRenderer.send('send-to-sidecar', { action: 'get-session-status' });

    // Set initial ignore state: Pass transparency but keep tracking
    window.electron.ipcRenderer.send('set-ignore-mouse-events', true, { forward: true });

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  useEffect(() => {
    let poll: ReturnType<typeof setInterval> | undefined;
    if (isLoggingIn) {
      poll = setInterval(() => {
        window.electron.ipcRenderer.send('send-to-sidecar', { action: 'check-auth', payload: sessionId });
      }, 3000);
    }
    return () => { if (poll) clearInterval(poll); };
  }, [isLoggingIn, sessionId]);

  const updateSetting = (key: string, val: any) => {
    setSettings((prev: any) => ({ ...prev, [key]: val }));
    window.electron.ipcRenderer.send('send-to-sidecar', { action: 'update-setting', payload: { key, val } });
    if (key === 'stealth_mode') window.electron.ipcRenderer.send('update-stealth', val);
    if (key === 'opacity') window.electron.ipcRenderer.send('set-opacity', val);
    if (key === 'hotkey') window.electron.ipcRenderer.send('re-register-hotkey', val);
  };

  const toggleDrawer = (mode: DrawerMode) => {
    if (drawerOpen && drawerMode === mode) {
      setDrawerOpen(false);
    } else {
      setDrawerMode(mode);
      setDrawerOpen(true);
    }
  };

  const handleMicClick = () => {
    if (!isAuthorized) {
      toggleDrawer('account');
      return;
    }
    const ns = !isLive;
    setIsLive(ns);
    window.electron.ipcRenderer.send('toggle-listening', ns);

    // Start a paid session on first mic activation
    if (ns && !sessionActive) {
      console.log("UI: Requesting session start...");
      window.electron.ipcRenderer.send('send-to-sidecar', { action: 'start-session' });
    }
  };

  const handleLockedClick = (mode: DrawerMode) => {
    if (!isAuthorized) {
      toggleDrawer('account');
    } else {
      toggleDrawer(mode);
    }
  };

  const handleEmailSignIn = () => {
    if (!loginEmail.trim() || !loginToken.trim()) return;
    setIsLoggingIn(true);
    window.electron.ipcRenderer.send('send-to-sidecar', {
      action: 'login-token',
      payload: { email: loginEmail.trim(), token: loginToken.trim() }
    });
  };

  // Sync drawer status to Main for hit-testing
  useEffect(() => {
    window.electron.ipcRenderer.send('set-drawer-status', drawerOpen);
  }, [drawerOpen]);

  return (
    <div className={`app-container platform-${platform === 'darwin' ? 'mac' : 'win'} ${settings.light_mode ? 'light-mode' : ''}`}>

      {/* Main Pill — always centered */}
      <motion.div
        layout
        className={`floating-pill ${!isAuthorized ? 'pill-locked' : 'pill-active'}`}
        initial={{ y: -50, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={springGentle}
      >
        <div className="pill-content">
          <div className="pill-left">
            <button className="icon-circle no-drag" onClick={() => toggleDrawer('account')}>
              <User size={18} />
            </button>
            <div className={`status-indicator ${isError ? 'error' : (isLive ? 'pulse' : '')}`} />
            <div className="brand-title">
              NEBULA <span style={{ color: 'var(--text-dim)', opacity: 0.6 }}>// {status}</span>
            </div>
          </div>

          <div className="pill-right">
            {sessionActive && (
              <div className={`session-timer no-drag ${timerUrgent ? 'urgent' : ''}`} onClick={handleMicClick} style={{ cursor: 'pointer' }}>
                {formatCountdown(remainingMs)}
              </div>
            )}

            {!isAuthorized ? (
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                className="btn-premium no-drag btn-locked"
                onClick={() => handleLockedClick('strategy')}
              >
                <Lock size={12} /> STRATEGY
              </motion.button>
            ) : (
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                className={`btn-premium no-drag ${drawerMode === 'strategy' && drawerOpen ? 'btn-accent' : ''}`}
                onClick={() => toggleDrawer('strategy')}
              >
                <Terminal size={14} /> STRATEGY
              </motion.button>
            )}

            <button
              className="icon-circle no-drag"
              onClick={() => toggleDrawer('settings')}
            >
              <Settings size={18} />
            </button>

            <button
              className={`icon-circle no-drag ${isLive ? 'btn-accent' : ''} ${!isAuthorized ? 'btn-locked' : ''}`}
              onClick={handleMicClick}
              title={isLive ? "Pause Session" : "Start Session"}
            >
              {!isAuthorized ? (
                <Lock size={14} />
              ) : isLive ? (
                <Pause size={18} fill="currentColor" />
              ) : (
                <Play size={18} fill="currentColor" />
              )}
            </button>

            <button className="icon-circle no-drag" onClick={() => window.close()}>
              <X size={18} />
            </button>
          </div>
        </div>
      </motion.div>

      {/* Multi-Pill Breadcrumbs (v19.0) */}
      <AnimatePresence mode="popLayout">
        {(transcript || history.length > 0) && (
          <motion.div
            layout
            variants={containerVariants}
            initial="hidden"
            animate="visible"
            className="sub-pill-stack"
          >
            {history.map((item, idx) => {
              // Extract core question for display (concise v20.9)
              const extractCoreQuestion = (text: string) => {
                if (!text) return "";
                // Filter out common filler words and keep only the core command/question
                let clean = text.replace(/NEW\s+/i, '').replace(/[?*]/g, '').trim();
                const commonPhrases = ["can you", "could you", "explain", "tell me about", "what is", "how do I"];

                // For the button, keep it very short
                const words = clean.split(' ');
                if (words.length <= 3) return clean;
                return words.slice(0, 3).join(' ') + '...';
              };

              return (
                <motion.div
                  layout
                  key={`hist-${idx}-${item.q.substring(0, 10)}`}
                  className="sub-pill-item breadcrumb no-drag"
                  variants={pillVariants}
                  whileHover={{ scale: 1.02, backgroundColor: 'rgba(70, 70, 70, 0.6)', borderColor: 'var(--accent-primary)' }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => {
                    setAiResponse(item.a);
                    setDetectedStrategy(item.strategy);
                    setDrawerMode('response');
                    setDrawerOpen(true);
                  }}
                >
                  <div className="sub-pill-text">{extractCoreQuestion(item.q)}</div>
                </motion.div>
              );
            })}

            {transcript && (
              <motion.div
                layout
                key="active-transcript-pill"
                className="sub-pill-item active-transcript"
                variants={pillVariants}
              >
                <div className="sub-pill-text">{transcript}</div>
              </motion.div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Drawer */}
      <AnimatePresence>
        {drawerOpen && (drawerMode !== 'response' || aiResponse) && (
          <motion.div
            layout
            className="drawer-container"
            initial={{ y: -20, opacity: 0, scale: 0.98 }}
            animate={{ y: 0, opacity: 1, scale: 1 }}
            exit={{ y: -10, opacity: 0, scale: 0.98 }}
            transition={springGentle}
          >
            {/* Account */}
            {drawerMode === 'account' && (
              <div className="view-content">
                <div className="view-header">
                  <h2>ACCOUNT</h2>
                  <User size={18} color="var(--accent-secondary)" />
                </div>

                {account.plan === "GUEST" ? (
                  <div className="auth-panel">
                    <div className="auth-hero">
                      <div className="auth-hero-icon">
                        <LogIn size={24} color="var(--accent-primary)" />
                      </div>
                      <div>
                        <p className="auth-hero-title">SIGN IN TO NEBULA</p>
                        <p className="auth-hero-subtitle">You need an active session with at least 1 credit to use Nebula.</p>
                      </div>
                    </div>

                    <div className="auth-btn-group">
                      <button
                        className="auth-btn auth-btn-google no-drag"
                        onClick={() => {
                          setIsLoggingIn(true);
                          window.electron.ipcRenderer.send('send-to-sidecar', { action: 'login-google', payload: sessionId });
                        }}
                      >
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ flexShrink: 0 }}>
                          <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
                          <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                          <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
                          <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.47 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
                        </svg>
                        <span>CONTINUE WITH GOOGLE</span>
                      </button>

                      <button
                        className="auth-btn auth-btn-github no-drag"
                        onClick={() => {
                          setIsLoggingIn(true);
                          window.electron.ipcRenderer.send('send-to-sidecar', { action: 'login-github', payload: sessionId });
                        }}
                      >
                        <Github size={16} style={{ flexShrink: 0 }} />
                        <span>CONTINUE WITH GITHUB</span>
                      </button>
                    </div>

                    <div className="auth-divider">
                      <span>or sign in with account</span>
                    </div>

                    <div className="auth-email-group">
                      <div className="auth-input-row">
                        <Mail size={14} className="auth-input-icon" />
                        <input
                          className="auth-input no-drag"
                          type="email"
                          placeholder="Email address"
                          value={loginEmail}
                          onChange={(e) => setLoginEmail(e.target.value)}
                          onKeyDown={(e) => e.key === 'Enter' && handleEmailSignIn()}
                        />
                      </div>
                      <div className="auth-input-row">
                        <KeyRound size={14} className="auth-input-icon" />
                        <input
                          className="auth-input no-drag"
                          type="password"
                          placeholder="Access token / password"
                          value={loginToken}
                          onChange={(e) => setLoginToken(e.target.value)}
                          onKeyDown={(e) => e.key === 'Enter' && handleEmailSignIn()}
                        />
                      </div>
                      <button
                        className="auth-btn auth-btn-email no-drag"
                        onClick={handleEmailSignIn}
                        disabled={!loginEmail.trim() || !loginToken.trim()}
                      >
                        SIGN IN
                      </button>
                    </div>

                    {isLoggingIn && (
                      <div className="auth-status-bar">
                        <span className="auth-status-dot" />
                        <span>Waiting for verification...</span>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="account-panel">
                    <div className="account-avatar-row">
                      <div className="account-avatar">
                        {account.avatar_url ? (
                          <img src={account.avatar_url} alt="Profile" className="avatar-img" />
                        ) : (
                          account.display_name?.charAt(0).toUpperCase() || 'N'
                        )}
                      </div>
                      <div className="account-info">
                        <p className="account-name">{account.display_name}</p>
                        <p className="account-email">{account.email}</p>
                      </div>
                    </div>

                    <div className="account-credits-card">
                      <span className="card-label">Credits Remaining</span>
                      <div className="account-credits-row">
                        <span className={`account-credits-value ${account.credits === 0 ? 'credits-empty' : ''}`}>
                          {account.credits}
                        </span>
                        <span className="account-credits-label">{account.plan}</span>
                      </div>
                      {account.credits === 0 && (
                        <p className="credits-warning">⚠ No credits remaining. Top up to continue.</p>
                      )}
                      {sessionActive && (
                        <div className={`account-timer-row ${timerUrgent ? 'urgent' : ''}`}>
                          <span>Session expires in</span>
                          <span className="account-timer-value">{formatCountdown(remainingMs)}</span>
                        </div>
                      )}
                    </div>

                    <button
                      className="btn-premium btn-danger no-drag"
                      onClick={() => {
                        window.electron.ipcRenderer.send('send-to-sidecar', { action: 'logout' });
                        setAccount({ display_name: "", email: "", credits: 0, plan: "GUEST" });
                        // Stop session timer on logout
                        if (timerRef.current) clearInterval(timerRef.current);
                        setSessionStartTime(null);
                        setIsLive(false);
                      }}
                    >
                      SIGN OUT
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* Strategy — gated */}
            {drawerMode === 'strategy' && (
              <div className="view-content">
                <div className="view-header">
                  <h2>STRATEGY</h2>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button className="btn-premium" onClick={async () => {
                      const res = await window.electron.ipcRenderer.invoke('open-file-dialog');
                      if (res) {
                        if (typeof res === 'object' && res.type === 'link') {
                          // PDF/Word — Delegate to Sidecar Parser
                          window.electron.ipcRenderer.send('send-to-sidecar', { action: 'parse-file', payload: res.path });
                        } else {
                          // Simple Text
                          setContextText(res);
                          window.electron.ipcRenderer.send('send-to-sidecar', { action: 'update-context', payload: res });
                        }
                      }
                    }}>
                      <Upload size={14} /> Resume
                    </button>
                    <button className="btn-premium" onClick={() => {
                      const url = prompt("Website URL:");
                      if (url) {
                        window.electron.ipcRenderer.send('send-to-sidecar', { action: 'fetch-context', payload: url });
                      }
                    }}>
                      <Globe size={14} /> URL
                    </button>
                  </div>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                  <div>
                    <span className="card-label">Intelligence Profile</span>
                    <SegmentedControl
                      options={['Auto', 'Standard', 'Coding', 'Systems', 'Behavioral']}
                      value={
                        settings.expert_mode === 'Auto' ? 'Auto' :
                          settings.expert_mode === 'Standard assistant' ? 'Standard' :
                            settings.expert_mode === 'Coding interview' ? 'Coding' :
                              settings.expert_mode === 'System design' ? 'Systems' : 'Behavioral'
                      }
                      onChange={(v) => {
                        const mapping: Record<string, string> = {
                          'Auto': 'Auto',
                          'Standard': 'Standard assistant',
                          'Coding': 'Coding interview',
                          'Systems': 'System design',
                          'Behavioral': 'Behavioral (Soft skills)'
                        };
                        updateSetting('expert_mode', mapping[v]);
                        if (v !== 'Auto') setDetectedStrategy(null);
                      }}
                    />
                    {settings.expert_mode === 'Auto' && detectedStrategy && (
                      <div className="auto-strategy-badge">
                        <span className="auto-strategy-dot" />
                        Auto-selected: <strong>{detectedStrategy}</strong>
                      </div>
                    )}
                  </div>
                  <textarea
                    className="input-field context-textarea"
                    placeholder="Paste job description or context..."
                    value={contextText}
                    onChange={(e) => setContextText(e.target.value)}
                  />
                  <button className="btn-premium btn-accent" style={{ color: 'black' }} onClick={() => {
                    window.electron.ipcRenderer.send('send-to-sidecar', { action: 'update-context', payload: contextText });
                    setDrawerOpen(false); // Fix: Dismiss drawer on manual sync v30.5
                  }}>
                    SYNC CONTEXT
                  </button>
                </div>
              </div>
            )}

            {/* Settings */}
            {drawerMode === 'settings' && (
              <div className="view-content scroll-y" style={{ maxHeight: '500px' }}>
                <div className="view-header">
                  <h2>SETTINGS</h2>
                  <Settings size={18} color="var(--accent-primary)" />
                </div>

                <div className="settings-section">
                  <button
                    className="w-full h-10 mb-4 rounded-xl bg-purple-500/20 hover:bg-purple-500/30 text-purple-200 border border-purple-500/30 font-medium transition-all text-xs"
                    onClick={() => {
                      setAiResponse("");
                      setStatus("MOCKING AI RESPONSE...");
                      window.electron.ipcRenderer.send('send-to-sidecar', {
                        action: 'fake-transcript',
                        payload: 'This is a test transcription to verify the AI pipeline is alive. Please respond with "SYSTEM OK".'
                      });
                    }}
                  >
                    🚀 DEBUG: TEST AI PIPELINE (Bypass Audio)
                  </button>
                  <h3><Shield size={14} /> PRIVACY</h3>
                  <div className="setting-row" onClick={() => updateSetting('stealth_mode', !settings.stealth_mode)}>
                    <span>Screen Protection</span>
                    <Toggle checked={settings.stealth_mode} onChange={(v) => updateSetting('stealth_mode', v)} />
                  </div>
                  <div className="setting-row" onClick={() => updateSetting('save_transcripts', !settings.save_transcripts)}>
                    <span>Save Transcripts</span>
                    <Toggle checked={settings.save_transcripts} onChange={(v) => updateSetting('save_transcripts', v)} />
                  </div>
                  <div className="setting-row" onClick={() => updateSetting('low_credit_alert', !settings.low_credit_alert)}>
                    <span>Low Credit Alert</span>
                    <Toggle checked={settings.low_credit_alert} onChange={(v) => updateSetting('low_credit_alert', v)} />
                  </div>
                  <div className="setting-row" onClick={() => updateSetting('session_end_warning', !settings.session_end_warning)}>
                    <span>Session End Warning</span>
                    <Toggle checked={settings.session_end_warning} onChange={(v) => updateSetting('session_end_warning', v)} />
                  </div>
                </div>

                <div className="settings-section">
                  <h3><Type size={14} /> DISPLAY</h3>
                  <div className="setting-row">
                    <span>Font Size</span>
                    <SegmentedControl
                      options={['13', '15', '18']}
                      value={settings.text_size.toString()}
                      onChange={(v) => updateSetting('text_size', parseInt(v))}
                    />
                  </div>
                  <div className="setting-row">
                    <span>Opacity</span>
                    <input
                      type="range"
                      className="no-drag"
                      min="50" max="255"
                      value={settings.opacity}
                      onChange={(e) => updateSetting('opacity', parseInt(e.target.value))}
                      onClick={(e) => e.stopPropagation()}
                    />
                  </div>
                  <div className="setting-row" onClick={() => updateSetting('light_mode', !settings.light_mode)}>
                    <span>Light Mode</span>
                    <Toggle checked={settings.light_mode} onChange={(v) => updateSetting('light_mode', v)} />
                  </div>
                </div>

                <div className="settings-section">
                  <h3><Zap size={14} /> SHORTCUTS</h3>
                  <div className="setting-row">
                    <span>Activation Hotkey</span>
                    <SegmentedControl
                      options={['F2', 'F3', 'F4', 'F5']}
                      value={settings.hotkey}
                      onChange={(v) => updateSetting('hotkey', v)}
                    />
                  </div>
                  <div className="setting-row" onClick={() => updateSetting('autoload_resume', !settings.autoload_resume)}>
                    <span>Autoload Resume</span>
                    <Toggle checked={settings.autoload_resume} onChange={(v) => updateSetting('autoload_resume', v)} />
                  </div>
                  <div className="setting-row" onClick={() => updateSetting('show_guide_startup', !settings.show_guide_startup)}>
                    <span>Show Guide on Start</span>
                    <Toggle checked={settings.show_guide_startup} onChange={(v) => updateSetting('show_guide_startup', v)} />
                  </div>
                </div>

                <button className="btn-premium full-width" style={{ marginTop: '20px' }} onClick={() => setShowOnboarding(true)}>
                  VIEW GUIDE
                </button>
              </div>
            )}

            {/* Response Stream (Answers Only v18.0) */}
            {drawerMode === 'response' && aiResponse && (
              <div className="drawer-view-mask">
                <div className="view-content response-drawer-content">
                  <div className="view-header">
                    <h2>NEBULA RESPONSE</h2>
                    <Sparkles size={16} color="var(--accent-primary)" />
                  </div>
                  <div className="nebula-response-card">
                    <ResponseRenderer text={aiResponse} />
                  </div>
                </div>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Onboarding */}
      <AnimatePresence>
        {showOnboarding && (
          <motion.div
            className="onboarding-overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setShowOnboarding(false)}
          >
            <motion.div
              className="onboarding-content"
              initial={{ scale: 0.9, y: 20 }}
              animate={{ scale: 1, y: 0 }}
            >
              <Sparkles size={56} color="var(--accent-primary)" style={{ marginBottom: '20px' }} />
              <h1>NEBULA</h1>
              <p style={{ fontSize: '16px', color: 'var(--text-secondary)' }}>Real-time AI interview intelligence.</p>
              <div className="guide-grid">
                <div className="guide-item">
                  <Terminal size={28} color="var(--accent-primary)" />
                  <strong>STRATEGY</strong>
                  <span style={{ fontSize: '12px', opacity: 0.7 }}>Set your context for tailored answers.</span>
                </div>
                <div className="guide-item">
                  <Mic size={28} color="var(--accent-primary)" />
                  <strong>LISTEN</strong>
                  <span style={{ fontSize: '12px', opacity: 0.7 }}>Tap mic or press hotkey to start.</span>
                </div>
                <div className="guide-item">
                  <Sparkles size={28} color="var(--accent-primary)" />
                  <strong>ANSWER</strong>
                  <span style={{ fontSize: '12px', opacity: 0.7 }}>Nebula responds in real-time.</span>
                </div>
              </div>
              <div className="dismiss-hint" style={{ marginTop: '40px' }}>TAP ANYWHERE TO CLOSE</div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function CodeBlock({ code, lang }: { code: string, lang: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="code-block-container no-drag">
      <div className="code-header">
        <span className="code-lang">{lang || 'code'}</span>
        <button className={`copy-btn ${copied ? 'copied' : ''}`} onClick={handleCopy}>
          {copied ? <Check size={12} /> : <Copy size={12} />}
          {copied ? 'COPIED' : 'COPY CODE'}
        </button>
      </div>
      <pre className="code-content">
        <code>{code}</code>
      </pre>
    </div>
  );
}

function ResponseRenderer({ text }: { text: string }) {
  // Split by code blocks: ```[lang]\n[code]\n```
  const parts = text.split(/(```[\s\S]*?```)/g);

  const renderTextWithBolding = (inputText: string) => {
    // Escape and replace **word** with <strong>word</strong> safely
    const subParts = inputText.split(/(\*\*.*?\*\*)/g);
    return subParts.map((sub, idx) => {
      if (sub.startsWith('**') && sub.endsWith('**')) {
        return <strong key={idx} style={{ color: 'var(--text-vibrant)', fontWeight: 800 }}>{sub.slice(2, -2)}</strong>;
      }
      return sub;
    });
  };

  return (
    <div className="response-renderer">
      {parts.map((part, i) => {
        if (part.startsWith('```')) {
          const match = part.match(/```(\w*)\n?([\s\S]*?)```/);
          if (match) {
            return <CodeBlock key={i} lang={match[1]} code={match[2].trim()} />;
          }
        }
        // Paragraphs with Bold support
        return part.split('\n').map((line, j) => (
          line.trim() ? <p key={`${i}-${j}`} style={{ margin: '12px 0', lineHeight: '1.7', color: 'var(--text-secondary)' }}>{renderTextWithBolding(line)}</p> : null
        ));
      })}
    </div>
  );
}

function SegmentedControl({ options, value, onChange }: { options: string[], value: any, onChange: (v: any) => void }) {
  return (
    <div className="segmented-control no-drag">
      {options.map(opt => (
        <div
          key={opt}
          className={`segment-item ${value === opt ? 'active' : ''}`}
          onClick={(e) => { e.stopPropagation(); onChange(opt); }}
        >
          {opt}
        </div>
      ))}
    </div>
  )
}

function Toggle({ checked, onChange }: { checked: boolean, onChange: (v: boolean) => void }) {
  return (
    <div className={`switch ${checked ? 'active' : ''}`} onClick={(e) => { e.stopPropagation(); onChange(!checked); }}>
      <motion.div
        className="handle"
        layout
        transition={{ type: "spring", stiffness: 700, damping: 40 }}
      />
    </div>
  )
}

export default App
