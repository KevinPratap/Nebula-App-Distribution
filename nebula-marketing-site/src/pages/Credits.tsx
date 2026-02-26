import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { FadeIn, StaggerContainer } from '../components/Animations'
import { Button } from '../components/Button'
import { Sparkles, Check, Zap, ShieldCheck, CreditCard } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { paymentService } from '../services/payment'

const PRICING_PLANS = [
    {
        id: 'basic',
        name: 'Starter Pack',
        credits: 2,
        price: 549,
        description: 'Great for a quick interview trial.',
        features: ['2 AI-Powered Sessions (30 Mins)', 'Neural Transcription', 'Desktop App Access', 'Real-time Overlay'],
        popular: false
    },
    {
        id: 'pro',
        name: 'Professional',
        credits: 3,
        price: 749,
        description: 'Perfect for a single high-stakes interview.',
        features: ['3 AI-Powered Sessions (45 Mins)', 'Priority AI Processing', 'Advanced Analytics', 'Cloud Sync', '24/7 Support'],
        popular: true
    },
    {
        id: 'elite',
        name: 'Elite Pack',
        credits: 5,
        price: 1199,
        description: 'Comprehensive preparation for an interview loop.',
        features: ['5 AI-Powered Sessions (75 Mins)', 'Unlimited Project History', 'Team Sharing', 'API Early Access', 'Dedicated Success Manager'],
        popular: false
    }
]

export default function Credits() {
    const { user, refreshUser } = useAuth()
    const [loading, setLoading] = useState(false)

    useEffect(() => {
        paymentService.loadRazorpay()
    }, [])

    const handlePurchase = async (plan: typeof PRICING_PLANS[0]) => {
        console.log(`[Payment] Initializing purchase for ${plan.credits} credits (₹${plan.price})...`);
        setLoading(true)
        try {
            const order = await paymentService.createOrder(plan.price, plan.credits);

            if (order.error) {
                alert(`Error: ${order.error}`);
                setLoading(false)
                return;
            }

            const options = {
                key: 'rzp_live_SEOz0JZJZKDLFD',
                amount: order.amount,
                currency: order.currency,
                name: 'Nebula AI',
                description: `Purchase ${plan.credits} Session Credits`,
                order_id: order.id,
                handler: async function (response: any) {
                    try {
                        const verification = await paymentService.verifyPayment({
                            razorpay_order_id: response.razorpay_order_id,
                            razorpay_payment_id: response.razorpay_payment_id,
                            razorpay_signature: response.razorpay_signature,
                            credits: plan.credits
                        });

                        if (verification.status === 'success') {
                            alert('Credits added successfully!');
                            await refreshUser();
                        } else {
                            alert('Payment verification failed.');
                        }
                    } catch (err: any) {
                        alert('Verification error: ' + err.message);
                    } finally {
                        setLoading(false)
                    }
                },
                modal: {
                    ondismiss: () => setLoading(false)
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
            alert('Payment system error: ' + error.message);
            setLoading(false)
        }
    };

    return (
        <div className="min-h-screen pt-32 pb-20 px-6">
            <div className="container mx-auto max-w-6xl">
                <FadeIn>
                    <div className="text-center mb-16">
                        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-nebula-purple/10 border border-nebula-purple/20 text-xs font-bold text-nebula-purple uppercase tracking-widest mb-4">
                            <Sparkles size={14} /> Pricing & Credits
                        </div>
                        <h1 className="text-5xl font-bold tracking-tight mb-4">Choose Your Power-Up</h1>
                        <p className="text-white/50 text-lg max-w-2xl mx-auto">
                            Get the credits you need to ace your next technical interview.
                            Each credit unlocks 15 minutes of real-time AI guidance.
                        </p>
                    </div>
                </FadeIn>

                <StaggerContainer className="grid grid-cols-1 md:grid-cols-3 gap-8">
                    {PRICING_PLANS.map((plan) => (
                        <motion.div
                            key={plan.id}
                            variants={{ hidden: { opacity: 0, scale: 0.95 }, show: { opacity: 1, scale: 1 } }}
                            className={`glass p-8 rounded-[2.5rem] border ${plan.popular ? 'border-nebula-purple bg-nebula-purple/5 relative' : 'border-white/5'} flex flex-col h-full`}
                        >
                            {plan.popular && (
                                <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-nebula-purple text-white text-[10px] font-bold uppercase tracking-widest px-4 py-1 rounded-full">
                                    Most Popular
                                </div>
                            )}

                            <div className="mb-8">
                                <h3 className="text-xl font-bold mb-2">{plan.name}</h3>
                                <div className="flex items-baseline gap-1 mb-4">
                                    <span className="text-4xl font-bold">₹{plan.price}</span>
                                    <span className="text-white/40 text-sm">/ {plan.credits} Credits</span>
                                </div>
                                <p className="text-sm text-white/50 leading-relaxed">
                                    {plan.description}
                                </p>
                            </div>

                            <div className="space-y-4 mb-10 flex-grow">
                                {plan.features.map((feature, i) => (
                                    <div key={i} className="flex items-center gap-3 text-sm text-white/70">
                                        <div className="w-5 h-5 rounded-full bg-white/5 flex items-center justify-center text-nebula-purple">
                                            <Check size={12} />
                                        </div>
                                        {feature}
                                    </div>
                                ))}
                            </div>

                            <Button
                                className="w-full"
                                variant={plan.popular ? 'primary' : 'secondary'}
                                onClick={() => handlePurchase(plan)}
                                disabled={loading}
                            >
                                {loading ? 'Processing...' : `Get ${plan.credits} Credits`}
                            </Button>
                        </motion.div>
                    ))}
                </StaggerContainer>

                <div className="mt-20">
                    <FadeIn>
                        <div className="glass p-10 rounded-[3rem] border border-white/5 flex flex-col md:flex-row items-center justify-between gap-10">
                            <div className="flex items-center gap-6">
                                <div className="w-16 h-16 rounded-2xl bg-nebula-purple/10 flex items-center justify-center text-nebula-purple">
                                    <ShieldCheck size={32} />
                                </div>
                                <div>
                                    <h4 className="text-xl font-bold mb-1 text-white">Secure Payments</h4>
                                    <p className="text-white/40 text-sm max-w-sm">All transactions are encrypted and processed securely via Razorpay.</p>
                                </div>
                            </div>
                            <div className="flex gap-4">
                                <div className="p-3 bg-white/5 rounded-xl border border-white/5">
                                    <CreditCard size={24} className="text-white/30" />
                                </div>
                                <div className="p-3 bg-white/5 rounded-xl border border-white/5">
                                    <Zap size={24} className="text-white/30" />
                                </div>
                            </div>
                        </div>
                    </FadeIn>
                </div>
            </div>
        </div>
    )
}
