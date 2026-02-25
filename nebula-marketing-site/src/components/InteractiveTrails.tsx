import { useRef, useEffect } from 'react'
import { motion, useSpring, useTransform } from 'framer-motion'

export const InteractiveTrails = () => {
    const mouseX = useSpring(0, { stiffness: 60, damping: 20 })
    const mouseY = useSpring(0, { stiffness: 60, damping: 20 })

    useEffect(() => {
        const handleMouseMove = (e: MouseEvent) => {
            mouseX.set(e.clientX)
            mouseY.set(e.clientY)
        }
        window.addEventListener('mousemove', handleMouseMove)
        return () => window.removeEventListener('mousemove', handleMouseMove)
    }, [mouseX, mouseY])

    return (
        <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden opacity-30">
            <svg className="w-full h-full">
                <Trail mouseX={mouseX} mouseY={mouseY} delay={0} color="#9F7AEA" />
                <Trail mouseX={mouseX} mouseY={mouseY} delay={0.1} color="#3B82F6" />
                <Trail mouseX={mouseX} mouseY={mouseY} delay={0.2} color="#6B46C1" />
            </svg>
        </div>
    )
}

const Trail = ({ mouseX, mouseY, delay, color }: any) => {
    const pathRef = useRef<SVGPathElement>(null)

    // Use framer-motion transformations to avoid React state-driven re-renders at 60fps
    const points = useSpring(0, { stiffness: 40, damping: 15 })

    useEffect(() => {
        const timer = setTimeout(() => {
            const update = () => {
                points.set(Date.now() * 0.001)
                requestAnimationFrame(update)
            }
            update()
        }, delay * 1000)
        return () => clearTimeout(timer)
    }, [points, delay])

    const d = useTransform([mouseX, mouseY, points], ([x, y, p]) => {
        const noise = Math.sin((p as number) + delay * 10) * 20
        return `M -100 ${y + noise} Q ${x / 2} ${y - noise} ${x} ${y} T ${window.innerWidth + 100} ${y + noise}`
    })

    return (
        <motion.path
            ref={pathRef}
            style={{ d }}
            stroke={color}
            strokeWidth="1"
            fill="transparent"
            strokeOpacity="0.2"
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ duration: 2, repeat: Infinity }}
        />
    )
}
