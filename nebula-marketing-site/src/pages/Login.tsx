import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Mail, Lock, ArrowRight, Github, CheckCircle2, AlertCircle } from 'lucide-react'
import { Button } from '../components/Button'
import { Modal } from '../components/Modal'
import { FadeIn } from '../components/Animations'
import { useAuth } from '../contexts/AuthContext'
import { apiService } from '../services/api'

export default function Login() {
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')
    const navigate = useNavigate()
    const { login } = useAuth()

    // Forgot Password States
    const [showForgotModal, setShowForgotModal] = useState(false)
    const [forgotEmail, setForgotEmail] = useState('')
    const [forgotStep, setForgotStep] = useState(1) // 1: Email, 2: Code/NewPass
    const [verificationCode, setVerificationCode] = useState('')
    const [newPass, setNewPass] = useState('')
    const [forgotLoading, setForgotLoading] = useState(false)
    const [forgotStatus, setForgotStatus] = useState<{ type: 'success' | 'error', message: string } | null>(null)

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setLoading(true)
        setError('')
        const result = await login(email, password)
        if (result.success) {
            navigate('/dashboard')
        } else {
            setError(result.error || 'Login failed')
        }
        setLoading(false)
    }

    const handleReqReset = async () => {
        if (!forgotEmail) return
        setForgotLoading(true)
        const result = await apiService.requestPasswordReset(forgotEmail)
        setForgotLoading(false)
        if (!result.error) {
            setForgotStep(2)
            setForgotStatus({ type: 'success', message: result.message })
        } else {
            setForgotStatus({ type: 'error', message: result.error })
        }
    }

    const handleReset = async () => {
        if (!verificationCode || !newPass) return
        setForgotLoading(true)
        const result = await apiService.resetPassword({
            email: forgotEmail,
            code: verificationCode,
            new_password: newPass
        })
        setForgotLoading(false)
        if (!result.error) {
            setForgotStatus({ type: 'success', message: "Password reset successful! Please log in." })
            setTimeout(() => {
                setShowForgotModal(false)
                setForgotStep(1)
                setForgotStatus(null)
            }, 2000)
        } else {
            setForgotStatus({ type: 'error', message: result.error })
        }
    }

    // Check for error in URL (social login failed)
    useEffect(() => {
        const params = new URLSearchParams(window.location.search)
        const errorMsg = params.get('error')
        if (errorMsg) {
            setError(errorMsg)
            window.history.replaceState({}, '', window.location.pathname)
        }
    }, [])

    const handleGoogleLogin = () => window.location.href = '/auth/google'
    const handleGithubLogin = () => window.location.href = '/auth/github'

    return (
        <div className="min-h-screen pt-32 pb-20 flex items-center justify-center px-6">
            <FadeIn direction="up">
                <div className="w-full max-w-md glass p-8 rounded-3xl border border-white/10 shadow-2xl relative overflow-hidden">
                    <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-nebula-purple to-nebula-blue" />

                    <div className="text-center mb-10">
                        <h1 className="text-3xl font-bold tracking-tight mb-2">Welcome Back</h1>
                        <p className="text-white/50">Log in to your Nebula account</p>
                    </div>

                    <div className="space-y-4 mb-8">
                        <Button variant="secondary" className="w-full justify-start px-6" onClick={handleGithubLogin}>
                            <Github size={20} className="mr-3 text-white/60" />
                            Continue with GitHub
                        </Button>
                        <Button variant="secondary" className="w-full justify-start px-6" onClick={handleGoogleLogin}>
                            <svg className="mr-3 w-5 h-5" viewBox="0 0 24 24">
                                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
                                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.26-.19-.58z" fill="#FBBC05" />
                                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
                            </svg>
                            Continue with Google
                        </Button>
                    </div>

                    <div className="relative mb-8">
                        <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-white/5" /></div>
                        <div className="relative flex justify-center text-xs uppercase tracking-widest"><span className="bg-[#0B0E14] px-4 text-white/30">Or continue with</span></div>
                    </div>

                    <form onSubmit={handleSubmit} className="space-y-6">
                        <div className="space-y-2">
                            <label className="text-sm font-medium text-white/70 ml-1">Email Address</label>
                            <div className="relative">
                                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 text-white/20" size={18} />
                                <input
                                    type="email"
                                    required
                                    className="w-full bg-white/5 border border-white/10 rounded-2xl py-3 pl-12 pr-4 text-white focus:outline-none focus:border-nebula-purple/50 transition-colors"
                                    placeholder="name@example.com"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                />
                            </div>
                        </div>

                        <div className="space-y-2">
                            <div className="flex justify-between items-center ml-1">
                                <label className="text-sm font-medium text-white/70">Password</label>
                                <button type="button" onClick={() => setShowForgotModal(true)} className="text-xs text-nebula-purple hover:underline">Forgot password?</button>
                            </div>
                            <div className="relative">
                                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 text-white/20" size={18} />
                                <input
                                    type="password"
                                    required
                                    className="w-full bg-white/5 border border-white/10 rounded-2xl py-3 pl-12 pr-4 text-white focus:outline-none focus:border-nebula-purple/50 transition-colors"
                                    placeholder="••••••••"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                />
                            </div>
                        </div>

                        {error && (
                            <motion.p initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="text-red-400 text-sm italic ml-1">
                                {error}
                            </motion.p>
                        )}

                        <Button type="submit" disabled={loading} className="w-full">
                            {loading ? 'Logging in...' : 'Log In'}
                            <ArrowRight size={18} className="ml-2" />
                        </Button>
                    </form>

                    <p className="text-center mt-8 text-sm text-white/40">
                        Don't have an account?{' '}
                        <Link to="/signup" className="text-nebula-purple hover:underline font-medium">Sign up</Link>
                    </p>
                </div>
            </FadeIn>

            {/* Forgot Password Modal */}
            <Modal
                isOpen={showForgotModal}
                onClose={() => { setShowForgotModal(false); setForgotStatus(null); }}
                title="Forgot Password"
                footer={
                    forgotStep === 1 ? (
                        <Button onClick={handleReqReset} disabled={forgotLoading}>
                            {forgotLoading ? 'Sending...' : 'Send Reset Code'}
                        </Button>
                    ) : (
                        <Button onClick={handleReset} disabled={forgotLoading}>
                            {forgotLoading ? 'Resetting...' : 'Reset Password'}
                        </Button>
                    )
                }
            >
                <div className="space-y-4">
                    <AnimatePresence mode="wait">
                        {forgotStatus && (
                            <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }} className={`p-3 rounded-xl flex items-center gap-3 text-sm mb-4 ${forgotStatus.type === 'success' ? 'bg-green-500/10 text-green-400 border border-green-500/20' : 'bg-red-500/10 text-red-400 border border-red-500/20'}`}>
                                {forgotStatus.type === 'success' ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
                                {forgotStatus.message}
                            </motion.div>
                        )}
                    </AnimatePresence>

                    {forgotStep === 1 ? (
                        <div className="space-y-4">
                            <p className="text-white/50 text-sm italic">Enter your account email to receive a verification code.</p>
                            <input
                                type="email"
                                value={forgotEmail}
                                onChange={(e) => setForgotEmail(e.target.value)}
                                className="w-full bg-white/5 border border-white/10 rounded-2xl py-3 px-4 text-white focus:outline-none focus:border-nebula-purple/50 transition-colors"
                                placeholder="your@email.com"
                            />
                        </div>
                    ) : (
                        <div className="space-y-4">
                            <p className="text-white/50 text-sm italic">Enter the 6-digit code sent to your email and your new password.</p>
                            <input
                                type="text"
                                maxLength={6}
                                value={verificationCode}
                                onChange={(e) => setVerificationCode(e.target.value)}
                                className="w-full bg-white/5 border border-white/10 rounded-2xl py-3 px-4 text-white focus:outline-none focus:border-nebula-purple/50 transition-colors text-center tracking-[1em] font-bold"
                                placeholder="000000"
                            />
                            <input
                                type="password"
                                value={newPass}
                                onChange={(e) => setNewPass(e.target.value)}
                                className="w-full bg-white/5 border border-white/10 rounded-2xl py-3 px-4 text-white focus:outline-none focus:border-nebula-purple/50 transition-colors"
                                placeholder="New password"
                            />
                        </div>
                    )}
                </div>
            </Modal>
        </div>
    )
}
