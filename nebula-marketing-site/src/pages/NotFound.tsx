import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import { Rocket, Home, MoveLeft } from 'lucide-react'
import { Button } from '../components/Button'

export default function NotFound() {
    return (
        <div className="min-h-screen flex items-center justify-center px-6 relative overflow-hidden">
            {/* Background elements */}
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full h-full pointer-events-none">
                <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-nebula-purple/10 blur-[100px] rounded-full animate-pulse" />
                <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-nebula-blue/10 blur-[100px] rounded-full animate-pulse delay-700" />
            </div>

            <div className="relative z-10 text-center max-w-2xl mx-auto">
                <motion.div
                    initial={{ y: 20, opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    transition={{ duration: 0.8 }}
                >
                    <div className="inline-flex items-center justify-center w-24 h-24 rounded-3xl bg-white/5 border border-white/10 mb-8 relative group">
                        <Rocket size={40} className="text-nebula-purple group-hover:rotate-12 transition-transform duration-500" />
                        <div className="absolute inset-0 bg-nebula-purple/20 blur-2xl opacity-0 group-hover:opacity-100 transition-opacity" />
                    </div>

                    <h1 className="text-8xl font-black mb-4 tracking-tighter gradient-text">404</h1>
                    <h2 className="text-3xl font-bold mb-6 tracking-tight">Lost in Deep Space</h2>
                    <p className="text-white/50 text-lg mb-10 leading-relaxed">
                        The signal you're looking for was lost in the cosmic void.
                        It seems the coordinates for this path don't exist in our nebula.
                    </p>

                    <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                        <Link to="/">
                            <Button size="lg" className="h-14 px-8">
                                <Home size={18} className="mr-2" />
                                Return Home
                            </Button>
                        </Link>
                        <button
                            onClick={() => window.history.back()}
                            className="flex items-center gap-2 text-white/50 hover:text-white transition-colors py-3 px-6 font-medium"
                        >
                            <MoveLeft size={18} />
                            Go Back
                        </button>
                    </div>
                </motion.div>
            </div>

            {/* Orbiting particles */}
            {[...Array(20)].map((_, i) => (
                <motion.div
                    key={i}
                    className="absolute w-1 h-1 bg-white/20 rounded-full"
                    animate={{
                        x: [
                            Math.random() * window.innerWidth,
                            Math.random() * window.innerWidth
                        ],
                        y: [
                            Math.random() * window.innerHeight,
                            Math.random() * window.innerHeight
                        ],
                        opacity: [0.2, 0.5, 0.2]
                    }}
                    transition={{
                        duration: 10 + Math.random() * 20,
                        repeat: Infinity,
                        ease: "linear"
                    }}
                />
            ))}
        </div>
    )
}
