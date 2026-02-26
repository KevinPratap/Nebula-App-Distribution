import { Link } from 'react-router-dom'
import { LogOut } from 'lucide-react'
import { Button } from './Button'
import { useAuth } from '../contexts/AuthContext'

export const Navbar = () => {
    const { user, logout } = useAuth();

    return (
        <nav className="fixed top-0 w-full z-50 glass border-b border-white/5">
            <div className="container mx-auto px-6 py-2 flex items-center justify-between">
                <Link to="/" className="flex items-center gap-2 text-xl font-bold tracking-tighter group">
                    <div className="relative h-20 w-auto min-w-[300px] flex items-center justify-start">
                        <img
                            src="/logo.png"
                            alt="Nebula Logo"
                            className="h-[80px] w-auto object-contain object-left scale-[2.5] group-hover:scale-[2.6] transition-transform duration-300 origin-left ml-4"
                        />
                    </div>
                </Link>
                <div className="hidden md:flex items-center gap-8 text-sm font-medium text-white/70">
                    <Link to="/#features" className="hover:text-white transition-colors">Features</Link>
                    <Link to="/#pricing" className="hover:text-white transition-colors">Pricing</Link>
                    <Link to="/download" className="hover:text-white transition-colors">Download</Link>
                </div>
                <div className="flex items-center gap-4">
                    {user ? (
                        <div className="flex items-center gap-3">
                            <Link to="/dashboard" className="flex items-center gap-3">
                                <div className="hidden sm:flex w-8 h-8 rounded-lg bg-gradient-to-br from-nebula-purple to-nebula-blue items-center justify-center text-xs font-bold overflow-hidden border border-white/10">
                                    {user?.avatar_url ? (
                                        <img
                                            src={user.avatar_url}
                                            alt="Avatar"
                                            className="w-full h-full object-cover"
                                            referrerPolicy="no-referrer"
                                        />
                                    ) : (
                                        user?.email?.[0]?.toUpperCase() ?? '?'
                                    )}
                                </div>
                                <Button size="sm" variant="secondary">Dashboard</Button>
                            </Link>
                            <button
                                onClick={() => logout()}
                                className="p-2 rounded-xl text-white/50 hover:text-red-400 hover:bg-red-400/10 transition-all"
                                title="Logout"
                            >
                                <LogOut size={18} />
                            </button>
                        </div>
                    ) : (
                        <>
                            <Link to="/login" className="text-sm font-medium text-white/70 hover:text-white transition-colors">Login</Link>
                            <Link to="/signup">
                                <Button size="sm">Get Started</Button>
                            </Link>
                        </>
                    )}
                </div>
            </div>
        </nav>
    )
}
