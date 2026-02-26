import { motion, useScroll, useTransform } from 'framer-motion'
import { Sparkles, ArrowRight, Monitor, Apple, Terminal, Check, Zap, Brain, Layout, ChevronDown, Mic, Lightbulb, Layers } from 'lucide-react'
import { useState, useEffect, useRef, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '../components/Button'
import { FadeIn, StaggerContainer } from '../components/Animations'
import { TiltCard } from '../components/TiltCard'
import { authService } from '../services/auth'
import { paymentService } from '../services/payment'
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'
import Hero3D from '../components/Hero3D'
import Footer from '../components/Footer'

function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs))
}

export default function Landing() {
    // Force cache bust to ensure Docker picks up the correct file version
    const [platform, setPlatform] = useState('windows')
    // Remove state, calculate directly to match Navbar behavior
    const isLoggedIn = authService.isLoggedIn()
    const containerRef = useRef<HTMLDivElement>(null)

    const { scrollYProgress } = useScroll({
        target: containerRef,
        offset: ["start start", "end start"]
    })

    const y1 = useTransform(scrollYProgress, [0, 1], [0, 200])
    const y2 = useTransform(scrollYProgress, [0, 1], [0, -150])
    const rotate = useTransform(scrollYProgress, [0, 1], [0, 10])

    useEffect(() => {
        const ua = navigator.userAgent
        if (ua.includes('Win')) setPlatform('windows')
        else if (ua.includes('Mac')) setPlatform('mac')
        else if (ua.includes('Linux')) setPlatform('linux')

        paymentService.loadRazorpay()
    }, [])

    const handleBuyCredits = async (amount: number, credits: number) => {
        try {
            const order = await paymentService.createOrder(amount, credits);
            if (order.error) {
                alert('Failed to create order. Please try again.');
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
                    const verification = await paymentService.verifyPayment({
                        razorpay_order_id: response.razorpay_order_id,
                        razorpay_payment_id: response.razorpay_payment_id,
                        razorpay_signature: response.razorpay_signature,
                        credits: credits
                    });

                    if (verification.status === 'success') {
                        alert('Credits added successfully!');
                        window.location.href = '/dashboard';
                    } else {
                        alert('Payment verification failed.');
                    }
                },
                prefill: {
                    email: localStorage.getItem('nebula_user_email') || '',
                },
                theme: {
                    color: '#9F7AEA',
                },
            };

            const rzp = new (window as any).Razorpay(options);
            rzp.open();
        } catch (error) {
            console.error('Payment Error:', error);
            alert('Something went wrong. Please try again.');
        }
    };

    return (
        <div ref={containerRef} className="pt-20">
            {/* Hero Section */}
            <section className="relative pt-20 pb-20 overflow-hidden min-h-screen flex items-center">
                <Hero3D />
                <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-[800px] bg-[radial-gradient(circle_at_center,rgba(159,122,234,0.15)_0,transparent_70%)] blur-[100px] pointer-events-none" />

                <div className="container mx-auto px-6 relative z-10 text-center">
                    <FadeIn>
                        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-white/10 text-xs font-semibold text-nebula-purple mb-8">
                            <Sparkles size={14} />
                            <span>NEBULA PUBLIC BETA</span>
                        </div>
                    </FadeIn>

                    <FadeIn delay={0.1}>
                        <h1 className="text-5xl md:text-8xl font-black tracking-tighter mb-6 leading-[0.9] perspective-1000">
                            <motion.span
                                className="inline-block bg-gradient-to-r from-white via-nebula-purple to-white bg-[length:200%_auto] bg-clip-text text-transparent"
                                animate={{ backgroundPosition: ['0% center', '200% center'] }}
                                transition={{ duration: 4, repeat: Infinity, ease: 'linear' }}
                            >
                                Meetings, <br />
                                <span className="text-nebula-purple">Mastered.</span>
                            </motion.span>
                        </h1>
                    </FadeIn>

                    <FadeIn delay={0.2}>
                        <p className="text-lg md:text-xl text-white/60 max-w-2xl mx-auto mb-10 leading-relaxed font-medium">
                            Your personal interview assistant. It listens, understands, and silently whispers the perfect answers to you in real-time. Never get stuck again.
                        </p>
                    </FadeIn>

                    <FadeIn delay={0.3}>
                        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-20 relative z-20">
                            <a href="/download">
                                <Button size="lg" className="group shadow-[0_0_30px_rgba(159,122,234,0.3)]">
                                    {platform === 'windows' && <Monitor size={18} className="mr-2" />}
                                    {platform === 'mac' && <Apple size={18} className="mr-2" />}
                                    {platform === 'linux' && <Terminal size={18} className="mr-2" />}
                                    Download Windows Beta
                                    <ArrowRight size={18} className="ml-2 transition-transform group-hover:translate-x-1" />
                                </Button>
                            </a>
                        </div>
                    </FadeIn>

                    {/* App Preview with Parallax */}
                    <div className="relative mx-auto max-w-5xl mt-12 px-4 shadow-2xl">
                        <motion.div
                            style={{ y: y1, rotateX: rotate }}
                            className="absolute -top-12 -left-12 w-24 h-24 bg-nebula-purple/20 blur-3xl rounded-full"
                        />
                        <motion.div
                            style={{ y: y2 }}
                            className="absolute -bottom-12 -right-12 w-32 h-32 bg-nebula-blue/20 blur-3xl rounded-full"
                        />

                        <FadeIn delay={0.4} direction="up" distance={50}>
                            <TiltCard className="relative group">
                                <div className="absolute -inset-1 bg-gradient-to-r from-nebula-purple to-nebula-blue rounded-3xl blur opacity-25 group-hover:opacity-50 transition duration-1000 group-hover:duration-200"></div>
                                <div className="glass rounded-3xl p-2 border border-white/10 relative">
                                    <div className="rounded-2xl overflow-hidden aspect-video bg-[#05070a] border border-white/5 flex items-center justify-center text-white/10 select-none shadow-inner">
                                        <div className="text-center">
                                            <motion.div
                                                animate={{ scale: [1, 1.1, 1], opacity: [0.3, 0.6, 0.3] }}
                                                transition={{ duration: 3, repeat: Infinity }}
                                                className="text-8xl mb-4"
                                            >
                                                <Sparkles className="w-24 h-24 text-nebula-purple drop-shadow-[0_0_15px_rgba(159,122,234,0.5)]" />
                                            </motion.div>
                                            <p className="font-bold tracking-[0.2em] text-xs uppercase opacity-40">Live Interview Assistance</p>
                                        </div>
                                    </div>
                                </div>
                            </TiltCard>
                        </FadeIn>
                    </div>
                </div>
            </section >

            {/* Logo Wall */}
            < section className="py-10 border-y border-white/5 bg-white/[0.01] overflow-hidden" >
                <div className="container mx-auto px-6">
                    <p className="text-center text-[10px] uppercase font-black tracking-[0.3em] text-white/20 mb-8">Helping candidates land roles at</p>
                    <div className="flex flex-wrap justify-center items-center gap-12 md:gap-20 opacity-30 grayscale hover:grayscale-0 transition-all duration-700">
                        <LogoPlaceholder name="GOOGLE" />
                        <LogoPlaceholder name="AMAZON" />
                        <LogoPlaceholder name="META" />
                        <LogoPlaceholder name="NETFLIX" />
                        <LogoPlaceholder name="UBER" />
                    </div>
                </div>
            </section >

            {/* Features Grid */}
            < section id="features" className="py-32 relative" >
                <div className="container mx-auto px-6">
                    <div className="text-center mb-24">
                        <h2 className="text-4xl md:text-5xl font-bold mb-4 tracking-tighter">Everything You Need to Win</h2>
                        <p className="text-white/40 max-w-md mx-auto">Don't just memorize answers. Have the smartest engineer in the room whispering them to you.</p>
                    </div>

                    <StaggerContainer>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-10">
                            <FeatureCard
                                icon={<Mic size={32} />}
                                title="It Listens & Understands"
                                description="Nebula hears the interviewer's question instantly, even with technical jargon or accents."
                            />
                            <FeatureCard
                                icon={<Lightbulb size={32} />}
                                title="Instant Answers"
                                description="Get the perfect answer displayed on your screen before they even finish asking the question."
                            />
                            <FeatureCard
                                icon={<Layers size={32} />}
                                title="Invisible Helper"
                                description="A discreet overlay that floats over Zoom or Teams. Only you can see it."
                            />
                        </div>
                    </StaggerContainer>
                </div>
            </section >

            {/* How It Works Section */}
            < section id="process" className="py-32 relative overflow-hidden" >
                <div className="container mx-auto px-6">
                    <div className="text-center mb-24">
                        <FadeIn>
                            <h2 className="text-4xl md:text-6xl font-black mb-6 tracking-tighter">Accidentally Unfair?</h2>
                            <p className="text-white/40 max-w-xl mx-auto text-lg leading-relaxed">Maybe. But using a calculator for math isn't cheating. Neither is this.</p>
                        </FadeIn>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-12 relative">
                        {/* Connecting Line (Desktop) */}
                        <div className="hidden md:block absolute top-1/2 left-0 w-full h-px bg-gradient-to-r from-transparent via-nebula-purple/30 to-transparent -translate-y-1/2 z-0" />

                        <ProcessStep
                            number="01"
                            title="Install"
                            description="Download and run Nebula on your computer. It takes 10 seconds."
                            icon={<Zap className="text-nebula-purple" />}
                        />
                        <ProcessStep
                            number="02"
                            title="Join Call"
                            description="Hop on your interview call. Nebula wakes up automatically."
                            icon={<Brain className="text-nebula-blue" />}
                        />
                        <ProcessStep
                            number="03"
                            title="Ace It"
                            description="Read the suggested answers naturally. Impress them with your knowledge."
                            icon={<Layout className="text-nebula-purple" />}
                        />
                    </div>
                </div>
            </section >

            {/* Interactive Preview / Visual Break */}
            < section className="py-32 bg-nebula-purple/[0.02] border-y border-white/5 relative overflow-hidden" >
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_70%_50%,rgba(159,122,234,0.1)_0,transparent_50%)]" />
                <div className="container mx-auto px-6 grid grid-cols-1 lg:grid-cols-2 gap-20 items-center">
                    <div>
                        <FadeIn direction="left">
                            <h2 className="text-5xl md:text-7xl font-black mb-8 tracking-tighter leading-none">Intelligence, <br /><span className="text-nebula-purple">Unbound.</span></h2>
                            <p className="text-white/50 text-xl leading-relaxed mb-10">
                                Nebula isn't just a tool; it's a cognitive extension. It builds a real-time semantic map of your conversation, delivering the sharpest insights exactly when you need them.
                            </p>
                            <div className="space-y-6">
                                <DetailItem title="Zero-Latency Core" description="Proprietary neural engine optimized for local execution." />
                                <DetailItem title="Semantic Mapping" description="Goes beyond keywords to understand core concepts." />
                                <DetailItem title="Privacy First" description="Encrypted data processing that stays in your control." />
                            </div>
                        </FadeIn>
                    </div>
                    <div className="relative">
                        <FadeIn direction="right">
                            <div className="glass rounded-[3rem] p-8 border border-white/10 relative z-10 shadow-2xl overflow-hidden">
                                <div className="absolute top-0 right-0 p-4 opacity-20"><Sparkles size={40} /></div>
                                <div className="space-y-4">
                                    <div className="flex items-center gap-3 mb-6">
                                        <div className="w-3 h-3 rounded-full bg-red-500/50" />
                                        <div className="w-3 h-3 rounded-full bg-yellow-500/50" />
                                        <div className="w-3 h-3 rounded-full bg-green-500/50" />
                                        <div className="h-px flex-1 bg-white/10 ml-4" />
                                    </div>
                                    <CodeLine delay={0} text="const nebula = new Intelligence();" />
                                    <CodeLine delay={0.2} text="await nebula.perceive(meeting_stream);" />
                                    <CodeLine delay={0.4} text="nebula.on('insight', (data) => {" className="text-nebula-purple" />
                                    <CodeLine delay={0.6} text="  renderOverlay(data.predicted_prompts);" className="pl-6" />
                                    <CodeLine delay={0.8} text="});" className="text-nebula-purple" />
                                </div>
                            </div>
                            {/* Decorative Elements */}
                            <motion.div
                                animate={{ y: [0, -20, 0] }}
                                transition={{ duration: 4, repeat: Infinity }}
                                className="absolute -top-10 -right-10 w-40 h-40 bg-nebula-purple/20 blur-3xl rounded-full -z-10"
                            />
                            <motion.div
                                animate={{ y: [0, 20, 0] }}
                                transition={{ duration: 5, repeat: Infinity }}
                                className="absolute -bottom-10 -left-10 w-40 h-40 bg-nebula-blue/20 blur-3xl rounded-full -z-10"
                            />
                        </FadeIn>
                    </div>
                </div>
            </section >


            {/* Pricing Section */}
            < section id="pricing" className="py-32 bg-white/[0.01]" >
                <div className="container mx-auto px-6 relative z-10">
                    <div className="text-center mb-20">
                        <h2 className="text-4xl md:text-5xl font-bold mb-4 tracking-tighter">Simple, Transparent</h2>
                        <p className="text-white/40">Choose the plan that fits your professional trajectory.</p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl mx-auto">
                        <PricingCard
                            title="Starter Pack"
                            price="₹549"
                            subtitle="2 Credits (30 mins)"
                            features={['Neural Transcription', 'Desktop App Access', 'Real-time Overlay']}
                            cta={isLoggedIn ? "Buy Now" : "Get Started"}
                            onAction={isLoggedIn ? () => handleBuyCredits(549, 2) : undefined}
                            link={!isLoggedIn ? "/signup" : undefined}
                        />
                        <PricingCard
                            title="Professional"
                            price="₹749"
                            subtitle="3 Credits (45 mins)"
                            featured={true}
                            features={['Priority AI Processing', 'Advanced Analytics', 'Cloud Sync', '24/7 Support']}
                            cta={isLoggedIn ? "Upgrade Now" : "Get Professional"}
                            onAction={isLoggedIn ? () => handleBuyCredits(749, 3) : undefined}
                            link={!isLoggedIn ? "/signup" : undefined}
                        />
                        <PricingCard
                            title="Elite Pack"
                            price="₹1199"
                            subtitle="5 Credits (75 mins)"
                            features={['Unlimited Project History', 'Team Sharing', 'API Early Access', 'Dedicated Success Manager']}
                            cta={isLoggedIn ? "Purchase Elite" : "Go Elite"}
                            onAction={isLoggedIn ? () => handleBuyCredits(1199, 5) : undefined}
                            link={!isLoggedIn ? "/signup" : undefined}
                        />
                    </div>
                </div>
            </section >

            {/* FAQ Section */}
            < section className="py-32" >
                <div className="container mx-auto px-6 max-w-4xl">
                    <div className="text-center mb-20">
                        <h2 className="text-4xl md:text-5xl font-black mb-4 tracking-tighter">Everything else you need to know.</h2>
                    </div>
                    <div className="space-y-4">
                        <FAQItem
                            question="How does Nebula detect the meeting apps?"
                            answer="Nebula uses a high-performance system-level hook that detects audio-visual patterns consistent with common meeting platforms like Zoom, Teams, and Slack. It works zero-latency without needing any plugins."
                        />
                        <FAQItem
                            question="Are my meetings recorded or stored?"
                            answer="Privacy is our prime directive. Nebula processes transcription locally and only stores metadata encrypted in your account for historical insights. Audio data is never stored on our servers."
                        />
                        <FAQItem
                            question="Can I use Nebula for free?"
                            answer="Every new pilot starts with free trial credits to experience the platform. After that, you can purchase credit bundles that fit your specific meeting frequency."
                        />
                        <FAQItem
                            question="Does it work with technical jargon?"
                            answer="Yes. Our Neural Engine is specifically trained on technical datasets, making it exceptionally accurate for software engineers, data scientists, and product managers."
                        />
                    </div>
                </div>
            </section >

            {/* Download Section */}
            < section id="download" className="py-32" >
                <div className="container mx-auto px-6 text-center">
                    <FadeIn>
                        <h2 className="text-5xl md:text-6xl font-bold mb-6 tracking-tighter">Ready to Ascend?</h2>
                        <p className="text-white/40 mb-16 max-w-xl mx-auto text-lg leading-relaxed">Join 10,000+ professionals using Nebula to redefine their productivity limits.</p>
                    </FadeIn>

                    <div className="flex flex-wrap justify-center gap-8">
                        <DownloadButton
                            platform="Windows"
                            icon={<Monitor size={32} />}
                            active={platform === 'windows'}
                            link="/Nebula-Installer.zip"
                        />
                        <DownloadButton
                            platform="macOS"
                            icon={<Apple size={32} />}
                            active={platform === 'mac'}
                            link="/Nebula-Installer.zip"
                        />
                        <DownloadButton
                            platform="Linux"
                            icon={<Terminal size={32} />}
                            active={platform === 'linux'}
                            link="/Nebula-Installer.zip"
                        />
                    </div>
                </div>
            </section >

            {/* Testimonials Section */}
            < section className="py-32 bg-nebula-blue/[0.01]" >
                <div className="container mx-auto px-6">
                    <div className="text-center mb-24">
                        <h2 className="text-4xl md:text-5xl font-black mb-4 tracking-tighter">Voice of the Community</h2>
                        <p className="text-white/40 max-w-md mx-auto">Real results from engineers at top-tier tech companies who used Nebula to bridge the gap.</p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                        <TestimonialCard
                            quote="Nebula was the differentiator for my L6 interview. The real-time semantic mapping for system design was exactly what I needed to stay structured."
                            author="Senior Staff Engineer"
                            company="Top 5 Tech"
                        />
                        <TestimonialCard
                            quote="Privacy was my #1 concern. Knowing Nebula processes everything locally gave me the confidence to use it during critical architectural rounds."
                            author="Technical Lead"
                            company="FinTech Unicorn"
                        />
                        <TestimonialCard
                            quote="The zero-latency transcription is incredible. It picked up every nuance of the distributed systems discussion without missing a beat."
                            author="SDE III"
                            company="E-commerce Giant"
                        />
                    </div>
                </div>
            </section >


            <Footer />
        </div >
    )
}

function TestimonialCard({ quote, author, company }: { quote: string, author: string, company: string }) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="glass p-10 rounded-[2.5rem] border border-white/5 relative group"
        >
            <div className="text-nebula-purple mb-6 opacity-30 group-hover:opacity-100 transition-opacity">
                <Sparkles size={24} />
            </div>
            <p className="text-lg font-medium text-white/80 leading-relaxed mb-8 italic">
                "{quote}"
            </p>
            <div className="flex flex-col">
                <span className="text-white font-bold">{author}</span>
                <span className="text-white/30 text-xs font-black uppercase tracking-widest">{company}</span>
            </div>
        </motion.div>
    )
}


function FeatureCard({ icon, title, description }: { icon: ReactNode, title: string, description: string }) {
    return (
        <motion.div
            variants={{
                hidden: { opacity: 0, y: 20 },
                show: { opacity: 1, y: 0 }
            }}
        >
            <TiltCard className="glass p-10 rounded-[2.5rem] border border-white/5 hover:border-nebula-purple/30 transition-all duration-500 group h-full">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-white/5 to-white/10 flex items-center justify-center text-nebula-purple mb-8 group-hover:scale-110 group-hover:rotate-6 transition-transform shadow-lg shadow-nebula-purple/5">
                    {icon}
                </div>
                <h3 className="text-2xl font-bold mb-4 tracking-tight text-white/90">{title}</h3>
                <p className="text-white/40 leading-relaxed text-sm font-medium">{description}</p>
            </TiltCard>
        </motion.div>
    )
}

function PricingCard({ title, price, subtitle, features, featured = false, cta, link, onAction }: { title: string, price: string, subtitle: string, features: string[], featured?: boolean, cta: string, link?: string, onAction?: () => void }) {
    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            className={cn(
                "relative p-10 rounded-[3rem] border transition-all flex flex-col group",
                featured ? "bg-white/[0.03] border-nebula-purple scale-105 z-10 shadow-2xl shadow-nebula-purple/10" : "glass border-white/5"
            )}
        >
            {featured && (
                <div className="absolute -top-5 left-1/2 -translate-x-1/2 px-5 py-1.5 rounded-full bg-nebula-purple text-[10px] font-black uppercase tracking-widest shadow-lg shadow-nebula-purple/30">
                    Best Value
                </div>
            )}
            <h3 className="text-2xl font-bold mb-3">{title}</h3>
            <div className="flex flex-col mb-10">
                <span className="text-5xl font-black">{price}</span>
                <span className="text-nebula-purple text-xs font-bold mt-2 uppercase tracking-wider">{subtitle}</span>
            </div>
            <ul className="space-y-5 mb-12 flex-1">
                {features.map((f, i) => (
                    <li key={i} className="flex items-center gap-4 text-sm text-white/60 font-medium">
                        <div className="w-6 h-6 rounded-full bg-nebula-purple/10 flex items-center justify-center text-nebula-purple shadow-sm">
                            <Check size={14} />
                        </div>
                        {f}
                    </li>
                ))}
            </ul>
            {link ? (
                <Link to={link} className="w-full">
                    <Button variant={featured ? 'primary' : 'secondary'} size="lg" className="w-full">
                        {cta}
                    </Button>
                </Link>
            ) : (
                <Button variant={featured ? 'primary' : 'secondary'} size="lg" className="w-full" onClick={onAction}>
                    {cta}
                </Button>
            )}
        </motion.div>
    )
}

function DownloadButton({ platform, icon, active, link }: { platform: string, icon: React.ReactNode, active: boolean, link: string }) {
    return (
        <motion.a
            href={link}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className={cn(
                "flex flex-col items-center gap-5 p-10 rounded-[2.5rem] border transition-all w-56 group",
                active ? "bg-nebula-purple/10 border-nebula-purple/50 text-nebula-purple shadow-2xl shadow-nebula-purple/10" : "glass border-white/5 text-white/40 hover:text-white/60"
            )}
        >
            <div className={cn("w-14 h-14 flex items-center justify-center transition-transform group-hover:scale-110", active ? "text-nebula-purple" : "text-white/20")}>
                {icon}
            </div>
            <span className="text-xl font-black tracking-tight">{platform}</span>
            {active && (
                <motion.span
                    initial={{ opacity: 0, y: 5 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="text-[10px] uppercase font-black tracking-widest text-nebula-purple/70"
                >
                    Optimized
                </motion.span>
            )}
        </motion.a>
    )
}

function LogoPlaceholder({ name }: { name: string }) {
    return (
        <span className="text-xl md:text-2xl font-black tracking-[0.4em] text-white/40 hover:text-white transition-colors cursor-default">
            {name}
        </span>
    )
}

function ProcessStep({ number, title, description, icon }: { number: string, title: string, description: string, icon: React.ReactNode }) {
    return (
        <div className="relative z-10">
            <div className="glass p-8 rounded-[2.5rem] border border-white/5 hover:border-white/10 transition-all group">
                <div className="flex items-start justify-between mb-8">
                    <div className="w-14 h-14 rounded-2xl bg-white/5 flex items-center justify-center text-2xl group-hover:scale-110 transition-transform">
                        {icon}
                    </div>
                    <span className="text-5xl font-black text-white/5 opacity-50">{number}</span>
                </div>
                <h3 className="text-2xl font-bold mb-4 tracking-tight">{title}</h3>
                <p className="text-white/40 leading-relaxed text-sm font-medium">{description}</p>
            </div>
        </div>
    )
}

function DetailItem({ title, description }: { title: string, description: string }) {
    return (
        <div className="flex gap-6">
            <div className="mt-1.5 w-1.5 h-1.5 rounded-full bg-nebula-purple shrink-0 shadow-[0_0_10px_rgba(159,122,234,0.5)]" />
            <div>
                <h4 className="text-white font-bold mb-1">{title}</h4>
                <p className="text-white/40 text-sm leading-relaxed">{description}</p>
            </div>
        </div>
    )
}

function CodeLine({ text, delay, className = "" }: { text: string, delay: number, className?: string }) {
    return (
        <motion.div
            initial={{ opacity: 0, x: -10 }}
            whileInView={{ opacity: 1, x: 0 }}
            transition={{ delay, duration: 0.5 }}
            className={cn("font-mono text-[13px] text-white/30", className)}
        >
            {text}
        </motion.div>
    )
}

function FAQItem({ question, answer }: { question: string, answer: string }) {
    const [isOpen, setIsOpen] = useState(false)
    return (
        <div className="glass rounded-3xl border border-white/5 overflow-hidden">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="w-full p-8 flex items-center justify-between text-left hover:bg-white/[0.02] transition-colors"
            >
                <span className="text-lg font-bold tracking-tight">{question}</span>
                <motion.div
                    animate={{ rotate: isOpen ? 180 : 0 }}
                    className="text-white/20"
                >
                    <ChevronDown size={20} />
                </motion.div>
            </button>
            <motion.div
                initial={false}
                animate={{ height: isOpen ? 'auto' : 0, opacity: isOpen ? 1 : 0 }}
                className="overflow-hidden"
            >
                <div className="px-8 pb-8 text-white/40 text-sm font-medium leading-relaxed">
                    {answer}
                </div>
            </motion.div>
        </div>
    )
}




