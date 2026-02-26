import { motion } from 'framer-motion'
import { Download as DownloadIcon, Cpu, Monitor, Shield, Zap, ArrowRight, CheckCircle2 } from 'lucide-react'
import { Button } from '../components/Button'
import { FadeIn, StaggerContainer } from '../components/Animations'

export default function Download() {
    return (
        <div className="min-h-screen pt-32 pb-20 px-6">
            <div className="container mx-auto">
                <div className="max-w-6xl mx-auto">
                    {/* Hero Section */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center mb-24">
                        <FadeIn direction="right">
                            <div className="space-y-6">
                                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-nebula-purple/10 border border-nebula-purple/20 text-nebula-purple text-xs font-bold uppercase tracking-widest">
                                    <Zap size={14} />
                                    NEBULA PUBLIC BETA v25
                                </div>
                                <h1 className="text-5xl lg:text-7xl font-bold tracking-tight leading-[1.1]">
                                    Unleash the <span className="gradient-text">Power</span> of Nebula.
                                </h1>
                                <p className="text-xl text-white/50 leading-relaxed max-w-lg">
                                    Experience real-time low-latency transcription and intelligent interview assistance directly on your desktop.
                                </p>
                                <div className="flex flex-col sm:flex-row gap-4 pt-4">
                                    <a href="/download">
                                        <Button size="lg" className="w-full sm:w-auto h-16 px-10 text-lg">
                                            Download for Windows
                                            <DownloadIcon size={20} className="ml-3" />
                                        </Button>
                                    </a>
                                    <div className="flex flex-col justify-center text-xs text-white/30 px-2">
                                        <span>Version 4.0.2 • 84MB</span>
                                        <span>Supported: Windows 10/11 (64-bit)</span>
                                    </div>
                                </div>
                            </div>
                        </FadeIn>

                        <FadeIn direction="left">
                            <div className="relative group">
                                <div className="absolute -inset-4 bg-gradient-to-r from-nebula-purple/20 to-nebula-blue/20 rounded-[40px] blur-3xl opacity-50 group-hover:opacity-75 transition-opacity duration-500" />
                                <div className="relative glass p-4 rounded-[40px] border border-white/10 shadow-2xl">
                                    <img
                                        src="https://images.unsplash.com/photo-1550751827-4bd374c3f58b?auto=format&fit=crop&q=80&w=1200"
                                        alt="Nebula Desktop App"
                                        className="rounded-[32px] w-full shadow-inner"
                                    />
                                    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2">
                                        <div className="w-20 h-20 rounded-full bg-nebula-purple/90 flex items-center justify-center animate-pulse">
                                            <Monitor size={32} className="text-white" />
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </FadeIn>
                    </div>

                    {/* Features Grid */}
                    <StaggerContainer>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-24">
                            <FeatureCard
                                icon={<Cpu />}
                                title="Low Latency"
                                desc="Powered by a custom local inference engine for instant processing."
                            />
                            <FeatureCard
                                icon={<Shield />}
                                title="Local-First"
                                desc="Your session data stays on your machine until you choose to sync."
                            />
                            <FeatureCard
                                icon={<Zap />}
                                title="Seamless Integration"
                                desc="Works with Zoom, Teams, Google Meet, and custom browser links."
                            />
                        </div>
                    </StaggerContainer>

                    {/* System Requirements */}
                    <FadeIn direction="up">
                        <div className="glass p-10 rounded-[40px] border border-white/10 relative overflow-hidden">
                            <div className="absolute top-0 right-0 p-12 text-nebula-blue/5 pointer-events-none">
                                <Monitor size={200} />
                            </div>
                            <h2 className="text-3xl font-bold mb-8 tracking-tight">System Requirements</h2>
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-10">
                                <ReqItem label="OS" value="Windows 8/10/11" sub="64-bit version" />
                                <ReqItem label="Processor" value="Dual Core 2.0GHz+" sub="or higher recommended" />
                                <ReqItem label="Memory" value="4 GB RAM" sub="8 GB for best experience" />
                                <ReqItem label="Storage" value="200 MB Space" sub="Minimum required" />
                            </div>
                        </div>
                    </FadeIn>

                </div>
            </div>
        </div>
    )
}

function FeatureCard({ icon, title, desc }: { icon: any, title: string, desc: string }) {
    return (
        <motion.div
            variants={{ hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } }}
            className="glass p-8 rounded-3xl border border-white/5 hover:border-white/10 transition-colors group"
        >
            <div className="w-12 h-12 rounded-2xl bg-white/5 flex items-center justify-center mb-6 group-hover:bg-nebula-purple/20 transition-colors duration-300">
                <div className="text-nebula-blue group-hover:text-nebula-purple transition-colors duration-300">
                    {icon}
                </div>
            </div>
            <h3 className="text-xl font-bold mb-3 tracking-tight">{title}</h3>
            <p className="text-sm text-white/50 leading-relaxed">{desc}</p>
        </motion.div>
    )
}

function ReqItem({ label, value, sub }: { label: string, value: string, sub: string }) {
    return (
        <div className="space-y-2">
            <p className="text-[10px] uppercase font-bold tracking-widest text-white/30">{label}</p>
            <p className="text-lg font-bold tracking-tight">{value}</p>
            <p className="text-xs text-white/40">{sub}</p>
        </div>
    )
}
