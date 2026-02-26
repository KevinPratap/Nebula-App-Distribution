import { Routes, Route, useLocation } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { useEffect } from 'react'
import Landing from './pages/Landing'
import Login from './pages/Login'
import Signup from './pages/Signup'
import Dashboard from './pages/Dashboard'
import { Navbar } from './components/Navbar'
import { CursorFollower } from './components/PointerEffects'
import { BackgroundEffects } from './components/BackgroundEffects'
import { InteractiveTrails } from './components/InteractiveTrails'
import Privacy from './pages/Privacy'
import Terms from './pages/Terms'
import Settings from './pages/Settings'
import Download from './pages/Download'
import Credits from './pages/Credits'
import NotFound from './pages/NotFound'
import { AuthProvider } from './contexts/AuthContext'
import { ProtectedRoute } from './components/ProtectedRoute'

function ScrollToTop() {
  const { pathname, hash } = useLocation()

  useEffect(() => {
    if (!hash) {
      // This scroll to top is now handled by the App's useEffect for general page navigation
      // window.scrollTo(0, 0)
    } else {
      const id = hash.replace('#', '')
      const element = document.getElementById(id)
      if (element) {
        element.scrollIntoView({ behavior: 'smooth' })
      }
    }
  }, [pathname, hash])

  return null
}

export default function App() {
  const location = useLocation()

  useEffect(() => {
    const titles: { [key: string]: string } = {
      '/': 'Nebula • AI Interview Assistant',
      '/login': 'Login • Nebula',
      '/signup': 'Get Started • Nebula',
      '/dashboard': 'Dashboard • Nebula',
      '/settings': 'Settings • Nebula',
      '/download': 'Download • Nebula',
      '/credits': 'Credits • Nebula',
      '/privacy': 'Privacy Policy • Nebula',
      '/terms': 'Terms of Service • Nebula',
    }

    document.title = titles[location.pathname] || '404 • Nebula'
    window.scrollTo(0, 0)
  }, [location])

  return (
    <AuthProvider>
      <div className="bg-nebula-dark min-h-screen relative overflow-hidden">
        <ScrollToTop />
        <BackgroundEffects />
        <InteractiveTrails />
        <CursorFollower />
        <Navbar />

        <AnimatePresence mode="wait">
          <motion.div
            key={location.pathname}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.3, ease: 'easeInOut' }}
            className="relative z-10"
          >
            <Routes location={location} key={location.pathname}>
              <Route path="/" element={<Landing />} />
              <Route path="/login" element={<Login />} />
              <Route path="/signup" element={<Signup />} />

              {/* Protected Routes */}
              <Route element={<ProtectedRoute />}>
                <Route path="/dashboard" element={<Dashboard />} />
              </Route>

              <Route path="/download" element={<Download />} />
              <Route path="/privacy" element={<Privacy />} />
              <Route path="/terms" element={<Terms />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/credits" element={<Credits />} />

              <Route path="*" element={<NotFound />} />
            </Routes>
          </motion.div>
        </AnimatePresence>
      </div>
    </AuthProvider>
  )
}
