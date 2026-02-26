import { useEffect, useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Download, Settings, LogOut, LayoutDashboard, Cpu, ShieldCheck, Sparkles, History as HistoryIcon, Calendar } from 'lucide-react'
import { Button } from '../components/Button'
import { FadeIn, StaggerContainer } from '../components/Animations'
import { authService } from '../services/auth'
import { paymentService } from '../services/payment'
import { apiService } from '../services/api'

export default function Dashboard() {
    const [user, setUser] = useState<any>(null)
    const [transactions, setTransactions] = useState<any[]>([])
    const [loading, setLoading] = useState(true)
    const navigate = useNavigate()

    useEffect(() => {
        const loadData = async () => {
            const data = await authService.refreshUser()
            if (data && !data.error && data.email) {
                setUser(data)
                setLoading(false)
            } else {
                navigate('/login')
            }
        }

        loadData()
        paymentService.loadRazorpay()
        apiService.getTransactions().then(res => {
            if (Array.isArray(res)) setTransactions(res);
        });
    }, [navigate])

    const handleBuyCredits = async (amount: number, credits: number) => {
        console.log(`[Payment] Initializing purchase for ${credits} credits (₹${amount})...`);
        try {
            const order = await paymentService.createOrder(amount, credits);
            console.log('[Payment] Order created:', order);

            if (order.error) {
                console.error('[Payment] Order error:', order.error);
                alert(`Error: ${order.error}`);
                return;
            }

            if (!(window as any).Razorpay) {
                console.error('[Payment] Razorpay SDK not loaded');
                alert('Payment system is initializing. Please wait a second and try again.');
                paymentService.loadRazorpay();
                return;
            }

            const options = {
                key: 'rzp_live_SEOz0JZJZKDLFD',
                amount: order.amount,
                currency: order.currency,
                name: 'Nebula AI',
                description: `Purchase ${credits} Session Credits`,
                order_id: order.id,
                handler: async function (response: any) {
                    console.log('[Payment] Success response:', response);
                    try {
                        const verification = await paymentService.verifyPayment({
                            razorpay_order_id: response.razorpay_order_id,
                            razorpay_payment_id: response.razorpay_payment_id,
                            razorpay_signature: response.razorpay_signature,
                            credits: credits
                        });

                        console.log('[Payment] Verification result:', verification);

                        if (verification.status === 'success' || verification.message === 'success') {
                            alert('Credits added successfully!');
                            const updated = await authService.refreshUser();
                            if (updated) setUser(updated);
                        } else {
                            alert('Payment verification failed: ' + (verification.message || 'Unknown error'));
                        }
                    } catch (vErr: any) {
                        console.error('[Payment] Verification Exception:', vErr);
                        alert('Error verifying payment: ' + vErr.message);
                    }
                },
                modal: {
                    ondismiss: function () {
                        console.log('[Payment] Window closed by user');
                    }
                },
                prefill: {
                    email: user?.email || '',
                },
                theme: {
                    color: '#9F7AEA',
                },
            };

            const rzp = new (window as any).Razorpay(options);
            rzp.open();
        } catch (error: any) {
            console.error('[Payment] Flow Error:', error);
            alert('Payment system error: ' + error.message);
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                    className="w-10 h-10 border-4 border-nebula-purple border-t-transparent rounded-full"
                />
            </div>
        )
    }

    // Safety check: if loading is done but user is still null, show error
    if (!user) {
        return (
            <div className="min-h-screen pt-32 pb-20 px-6 flex flex-col items-center justify-center text-center">
                <h2 className="text-2xl font-bold text-red-400 mb-4">Profile Load Failed</h2>
                <p className="text-white/50 mb-8">We couldn't load your account data.</p>
                <Button onClick={() => window.location.href = '/login'}>Return to Login</Button>
            </div>
        )
    }

    return (
        <div className="min-h-screen pt-32 pb-20 px-6">
            <div className="container mx-auto grid grid-cols-1 lg:grid-cols-4 gap-8">
                {/* Sidebar */}
                <aside className="lg:col-span-1 space-y-6">
                    <FadeIn direction="right">
                        <div className="glass p-6 rounded-3xl border border-white/10">
                            <div className="flex items-center gap-4 mb-8">
                                <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-nebula-purple to-nebula-blue flex items-center justify-center text-xl font-bold overflow-hidden">
                                    {user?.avatar_url ? (
                                        <img
                                            src={user.avatar_url}
                                            alt="User Avatar"
                                            className="w-full h-full object-cover"
                                            referrerPolicy="no-referrer"
                                        />
                                    ) : (
                                        user?.email?.[0]?.toUpperCase() ?? '?'
                                    )}
                                </div>
                                <div>
                                    <h3 className="font-bold tracking-tight truncate max-w-[120px]">
                                        {user?.display_name || user?.email?.split('@')?.[0] || 'User'}
                                    </h3>
                                    <p className="text-xs text-white/40 truncate max-w-[120px]">{user?.email || 'No Email'}</p>
                                </div>
                            </div>

                            <div className="space-y-1">
                                <SidebarLink icon={<LayoutDashboard size={18} />} label="Overview" to="/dashboard" active />
                                <SidebarLink icon={<Sparkles size={18} />} label="Add Credits" to="/credits" />
                                <SidebarLink icon={<Download size={18} />} label="Downloads" to="/download" />
                                <SidebarLink icon={<Settings size={18} />} label="Settings" to="/settings" />
                                <div className="pt-4 mt-4 border-t border-white/5">
                                    <button
                                        onClick={() => authService.logout()}
                                        className="flex items-center gap-3 w-full px-4 py-3 rounded-2xl text-sm font-medium text-red-400 hover:bg-red-400/10 transition-colors"
                                    >
                                        <LogOut size={18} />
                                        Log Out
                                    </button>
                                </div>
                            </div>
                        </div>
                    </FadeIn>
                </aside>

                {/* Main Content */}
                <main className="lg:col-span-3 space-y-8">
                    <FadeIn direction="up">
                        <div id="credits-section" className="glass p-8 rounded-3xl border border-white/10 relative overflow-hidden scroll-mt-32">
                            <div className="absolute top-0 right-0 p-8 text-nebula-purple/10 pointer-events-none">
                                <Sparkles size={120} />
                            </div>

                            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 relative z-10">
                                <div>
                                    <h2 className="text-3xl font-bold tracking-tight mb-2">Usage & Credits</h2>
                                    <p className="text-white/50">Manage your Nebula credits and session allocation.</p>
                                </div>
                                <div className="flex items-center gap-3 px-4 py-2 rounded-full bg-nebula-purple/10 border border-nebula-purple/20 text-nebula-purple text-xs font-bold uppercase tracking-widest">
                                    <Sparkles size={14} />
                                    Active Session
                                </div>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mt-10">
                                <StatusItem label="Credits Remaining" value={`${user?.credits ?? 0} Credits`} />
                                <StatusItem label="Time Available" value={`${(user?.credits ?? 0) * 15} Mins`} />
                                <StatusItem label="Usage Rate" value="1 Credit / 15m" />
                            </div>

                            <div className="mt-10">
                                <Link to="/credits">
                                    <Button className="w-full md:w-auto">
                                        Buy More Credits
                                    </Button>
                                </Link>
                            </div>
                        </div>
                    </FadeIn>

                    <StaggerContainer>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                            <DashboardCard
                                icon={<Cpu className="text-nebula-blue" />}
                                title="Desktop Optimizer"
                                desc="Download the optimized desktop client for the best performance."
                                cta="Download App"
                                to="/download"
                            />
                            <DashboardCard
                                icon={<ShieldCheck className="text-nebula-purple" />}
                                title="Security Settings"
                                desc="Manage your account security and session permissions."
                                cta="Manage Settings"
                                to="/settings"
                            />
                        </div>
                    </StaggerContainer>
                </main>
            </div>
        </div>
    )
}

function SidebarLink({ icon, label, active = false, to = "#" }: { icon: any, label: string, active?: boolean, to?: string }) {
    const isAnchor = to.startsWith('#')
    const Content = (
        <>
            {icon}
            {label}
        </>
    )

    const className = cn(
        "flex items-center gap-3 w-full px-4 py-3 rounded-2xl text-sm font-medium transition-all text-left",
        active ? "bg-nebula-purple/10 text-nebula-purple" : "text-white/50 hover:bg-white/5 hover:text-white"
    )

    if (isAnchor) {
        return <a href={to} className={className}>{Content}</a>
    }

    return (
        <Link to={to} className={className}>
            {Content}
        </Link>
    )
}

function StatusItem({ label, value }: { label: string, value: string }) {
    return (
        <div className="space-y-1">
            <p className="text-[10px] uppercase font-bold tracking-widest text-white/30">{label}</p>
            <p className="text-xl font-bold tracking-tight">{value}</p>
        </div>
    )
}

function DashboardCard({ icon, title, desc, cta, to }: { icon: any, title: string, desc: string, cta: string, to?: string }) {
    return (
        <motion.div
            variants={{ hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } }}
            className="glass p-8 rounded-3xl border border-white/5 hover:border-white/10 transition-colors"
        >
            <div className="w-12 h-12 rounded-2xl bg-white/5 flex items-center justify-center mb-6">
                {icon}
            </div>
            <h3 className="text-xl font-bold mb-3 tracking-tight">{title}</h3>
            <p className="text-sm text-white/50 leading-relaxed mb-8">{desc}</p>
            {to ? (
                <Link to={to} className="w-full block">
                    <Button variant="secondary" size="sm" className="w-full">{cta}</Button>
                </Link>
            ) : (
                <Button variant="secondary" size="sm" className="w-full">{cta}</Button>
            )}
        </motion.div>
    )
}

// Helper from before
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs))
}
