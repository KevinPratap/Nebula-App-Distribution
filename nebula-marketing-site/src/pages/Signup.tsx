import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Mail, Lock, ArrowRight, Github, CheckCircle2 } from 'lucide-react'
import { Button } from '../components/Button'
import { FadeIn } from '../components/Animations'
import { authService } from '../services/auth'
import { useAuth } from '../contexts/AuthContext'

export default function Signup() {
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [confirmPassword, setConfirmPassword] = useState('')
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')
    const navigate = useNavigate()
    const { refreshUser } = useAuth()

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        if (password !== confirmPassword) {
            setError('Passwords do not match')
            return
        }

        setLoading(true)
        setError('')

        const result = await authService.signup(email, password)
        if (result.success) {
            // Force update global context state
            await refreshUser()
            navigate('/dashboard')
        } else {
            setError(result.error || 'Signup failed')
        }
        setLoading(false)
    }

    // Check for error in URL (social login failed)
    useEffect(() => {
        const params = new URLSearchParams(window.location.search)
        const errorMsg = params.get('error')
        if (errorMsg) {
            setError(errorMsg)
            // Clear URL
            window.history.replaceState({}, '', window.location.pathname)
        }
    }, [])

    const handleGoogleLogin = () => {
        window.location.href = '/auth/google'
    }

    const handleGithubLogin = () => {
        window.location.href = '/auth/github'
    }

    return (
        <div className="min-h-screen pt-32 pb-20 flex items-center justify-center px-6">
            <FadeIn direction="up">
                <div className="w-full max-w-md glass p-8 rounded-3xl border border-white/10 shadow-2xl relative overflow-hidden">
                    <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-nebula-purple to-nebula-blue" />

                    <div className="text-center mb-10">
                        <h1 className="text-3xl font-bold tracking-tight mb-2">Create Account</h1>
                        <p className="text-white/50">Get your first 15-minute session free</p>
                    </div>

                    <div className="space-y-4 mb-8">
                        <Button variant="secondary" className="w-full justify-start px-6" onClick={handleGithubLogin}>
                            <Github size={20} className="mr-3 text-white/60" />
                            Continue with GitHub
                        </Button>
                        <Button variant="secondary" className="w-full justify-start px-6" onClick={handleGoogleLogin}>
                            <svg className="mr-3 w-5 h-5" viewBox="0 0 24 24">
                                <path
                                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                                    fill="#4285F4"
                                />
                                <path
                                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                                    fill="#34A853"
                                />
                                <path
                                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.26-.19-.58z"
                                    fill="#FBBC05"
                                />
                                <path
                                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                                    fill="#EA4335"
                                />
                            </svg>
                            Continue with Google
                        </Button>
                    </div>

                    <div className="relative mb-8">
                        <div className="absolute inset-0 flex items-center">
                            <div className="w-full border-t border-white/5" />
                        </div>
                        <div className="relative flex justify-center text-xs uppercase tracking-widest">
                            <span className="bg-[#0B0E14] px-4 text-white/30">Or continue with</span>
                        </div>
                    </div>

                    <form onSubmit={handleSubmit} className="space-y-5">
                        <div className="space-y-2">
                            <label className="text-sm font-medium text-white/70 ml-1">Email Address</label>
                            <div className="relative">
                                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 text-white/20" size={18} />
                                <input
                                    type="email"
                                    required
                                    className="w-full bg-white/5 border border-white/10 rounded-2xl py-3 pl-12 pr-4 text-white placeholder:text-white/20 focus:outline-none focus:border-nebula-purple/50 transition-colors"
                                    placeholder="name@example.com"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                />
                            </div>
                        </div>

                        <div className="space-y-2">
                            <label className="text-sm font-medium text-white/70 ml-1">Password</label>
                            <div className="relative">
                                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 text-white/20" size={18} />
                                <input
                                    type="password"
                                    required
                                    className="w-full bg-white/5 border border-white/10 rounded-2xl py-3 pl-12 pr-4 text-white placeholder:text-white/20 focus:outline-none focus:border-nebula-purple/50 transition-colors"
                                    placeholder="••••••••"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                />
                            </div>
                        </div>

                        <div className="space-y-2">
                            <label className="text-sm font-medium text-white/70 ml-1">Confirm Password</label>
                            <div className="relative">
                                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 text-white/20" size={18} />
                                <input
                                    type="password"
                                    required
                                    className="w-full bg-white/5 border border-white/10 rounded-2xl py-3 pl-12 pr-4 text-white placeholder:text-white/20 focus:outline-none focus:border-nebula-purple/50 transition-colors"
                                    placeholder="••••••••"
                                    value={confirmPassword}
                                    onChange={(e) => setConfirmPassword(e.target.value)}
                                />
                            </div>
                        </div>

                        {error && (
                            <motion.p
                                initial={{ opacity: 0, y: -10 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="text-red-400 text-sm italic ml-1"
                            >
                                {error}
                            </motion.p>
                        )}

                        <div className="pt-2">
                            <Button type="submit" disabled={loading} className="w-full">
                                {loading ? 'Creating Account...' : 'Get Started for Free'}
                                <ArrowRight size={18} className="ml-2" />
                            </Button>
                        </div>
                    </form>

                    <div className="mt-8 space-y-3">
                        <div className="flex items-center gap-2 text-xs text-white/30 ml-1">
                            <CheckCircle2 size={14} className="text-nebula-purple" />
                            <span>No credit card required for trial</span>
                        </div>
                        <div className="flex items-center gap-2 text-xs text-white/30 ml-1">
                            <CheckCircle2 size={14} className="text-nebula-purple" />
                            <span>Cancel anytime in one click</span>
                        </div>
                    </div>

                    <p className="text-center mt-8 text-sm text-white/40">
                        Already have an account?{' '}
                        <Link to="/login" className="text-nebula-purple hover:underline font-medium">Log in</Link>
                    </p>
                </div>
            </FadeIn>
        </div>
    )
}
